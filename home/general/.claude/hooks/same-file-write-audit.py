#!/usr/bin/env python3
'''PostToolUse detector: two different writers touching the same file.

Fires after Edit / Write. Keeps a short rolling ledger of recent writes per working
directory, keyed by absolute path and *writer identity*. Claude Code populates
`agent_id`/`agent_type` in the hook stdin only for subagent-originated calls, so the
writer is that agent id (or 'main-thread' when absent). When a path is written by one
writer and then, within a short window, by a DIFFERENT writer, that is the silent
same-file collision we want to surface — a nested fork or two overlapping agents
editing one file with no awareness of each other. We inject a non-blocking warning so
it is never silent again. A single agent making rapid successive edits to one file
shares one writer id, so it never trips this.

Fail-safe: any parse/IO hiccup returns cleanly and emits nothing.
'''
import hashlib
import json
import os
import sys
import time
from pathlib import Path

WINDOW_S = 180.0     # how long a prior write stays 'live' for collision purposes
STATE_DIR = Path.home() / '.claude' / 'hooks' / 'state'


def writer_id(data: dict) -> str:
    return str(data.get('agent_id') or data.get('agent_type') or 'main-thread')


def ledger_path(cwd: str) -> Path:
    key = hashlib.sha1((cwd or 'nocwd').encode()).hexdigest()[:16]
    return STATE_DIR / f'writes-{key}.json'


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
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
    cwd = data.get('cwd', '') or os.getcwd()
    store = ledger_path(cwd)

    try:
        entries = json.loads(store.read_text())
    except (OSError, json.JSONDecodeError, ValueError):
        entries = []

    # Prune stale, find a recent write to the same path by a different writer.
    fresh, clash = [], None
    for e in entries:
        if now - e.get('ts', 0) > WINDOW_S:
            continue
        fresh.append(e)
        if e.get('path') == path and e.get('writer') != me:
            clash = e

    fresh.append({'ts': now, 'path': path, 'writer': me})
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps(fresh))
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
