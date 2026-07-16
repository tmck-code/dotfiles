#!/usr/bin/env python3
'''PostToolUse detector: two different writers touching the same file.

Fires after Edit / Write. Keeps a short-lived ledger entry per *absolute file path*,
shared globally across every session on the machine (not scoped to a working
directory or session id), keyed by path and *writer identity*. Claude Code populates
`agent_id`/`agent_type` in the hook stdin only for subagent-originated calls, so the
writer is that agent id, qualified with the session id (or 'main-thread:<session>'
when absent) so writers from different sessions never alias to the same id. When a
path is written by one writer and then, within a short window, by a DIFFERENT writer
— whether that's a sibling agent in this session or an entirely separate session
elsewhere on the machine — that is the silent same-file collision we want to surface.
We inject a non-blocking warning so it is never silent again. A single agent making
rapid successive edits to one file shares one writer id, so it never trips this.

The ledger is one tiny state file per path (keyed by a hash of the path, not the
cwd), guarded with an flock so concurrent processes touching the same path do a safe
read-modify-write instead of racing each other.

Fail-safe: any parse/IO/lock hiccup returns cleanly and emits nothing.
'''
import fcntl
import hashlib
import json
import os
import sys
import time
from pathlib import Path

WINDOW_S    = 180.0  # how long a prior write stays 'live' for collision purposes
LIVENESS_S  = 600.0  # passive mtime fallback: how long a session's transcript file
                      # can go unmodified before we treat that session as dead. This
                      # only matters for an UNCLEAN death (crash/kill) where SessionEnd
                      # never fires; a clean exit or /clear is reclaimed exactly and
                      # immediately by the SessionEnd cleanup path below instead.
STATE_DIR = Path.home() / '.claude' / 'hooks' / 'state'


def writer_id(data: dict) -> str:
    agent = data.get('agent_id') or data.get('agent_type') or 'main-thread'
    session = data.get('session_id') or 'nosession'
    return f'{agent}:{session}'


def ledger_path(path: str) -> Path:
    key = hashlib.sha1(path.encode()).hexdigest()[:16]
    return STATE_DIR / f'write-{key}.json'


def session_alive(transcript_path: str) -> bool:
    if not transcript_path:
        return True  # unknown -> don't suppress, fall back to WINDOW_S-only behavior
    try:
        mtime = os.path.getmtime(transcript_path)
    except OSError:
        return False  # transcript is gone -> session no longer exists
    return (time.time() - mtime) <= LIVENESS_S


def cleanup_session(session_id: str) -> None:
    if not session_id:
        return
    try:
        for entry in STATE_DIR.glob('write-*.json'):
            try:
                with open(entry) as f:
                    prev = json.load(f)
                writer = prev.get('writer', '')
                _, _, writer_session = writer.rpartition(':')
                if writer_session == session_id:
                    entry.unlink()
            except (OSError, json.JSONDecodeError, ValueError):
                continue  # best-effort per-file; never abort the sweep
    except OSError:
        pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if data.get('hook_event_name') == 'SessionEnd':
        try:
            cleanup_session(data.get('session_id', ''))
        except Exception:
            pass  # must never raise/block
        return 0

    if data.get('tool_name', '') not in ('Edit', 'Write'):
        return 0

    tool_input = data.get('tool_input') or {}
    path = tool_input.get('file_path', '')
    if not path:
        return 0
    path = os.path.abspath(path)

    now = time.time()
    me = writer_id(data)
    store = ledger_path(path)
    transcript = data.get('agent_transcript_path') or data.get('transcript_path') or ''

    clash = None
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(store, 'a+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            try:
                prev = json.loads(f.read())
            except (json.JSONDecodeError, ValueError):
                prev = None
            if (
                prev
                and now - prev.get('ts', 0) <= WINDOW_S
                and prev.get('writer') != me
                and session_alive(prev.get('transcript', ''))
            ):
                clash = prev
            f.seek(0)
            f.truncate()
            json.dump({'ts': now, 'path': path, 'writer': me, 'transcript': transcript}, f)
    except OSError:
        pass  # ledger is best-effort; never block on it

    if clash is None:
        return 0

    ago = int(now - clash.get('ts', now))
    warn = (
        f'Same-file-write audit: `{path}` was just written by writer '
        f'"{clash.get("writer")}" {ago}s ago and now by "{me}" — two different '
        'writers on one file inside a short window. This is the silent lost-update '
        'pattern (a nested fork or two overlapping agents editing the same file). '
        'Confirm the edits did not clobber each other; enforce a single sole-writer '
        'for this file, or isolate parallel editors in their own git worktrees.'
    )
    json.dump(
        {
            'hookSpecificOutput': {
                'hookEventName':     'PostToolUse',
                'additionalContext': warn,
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
