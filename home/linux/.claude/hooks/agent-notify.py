#!/usr/bin/env python3
'''Desktop notifications for coding agents (Claude Code hooks and the OpenCode plugin).

One notification is kept per session: each new notification for a session
replaces the previous one instead of adding another entry to the tray.

Usage:
  agent-notify.py claude                       # Claude Code hook; reads hook JSON on stdin
  agent-notify.py send APP KEY TITLE BODY [URGENCY]
'''
from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path

NOTIFY_SEND = '/usr/bin/notify-send'
STATE_DIR   = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'agent-notify'
STATE_FILE  = STATE_DIR / 'ids.json'
MAX_KEYS    = 200
BODY_LIMIT  = 200

CLAUDE_APP = 'Claude Code'
# GNOME groups notifications by .desktop entry (see ~/.local/share/applications/).
DESKTOP_ENTRIES = {
    'Claude Code': ('claude-code', 'utilities-terminal'),
    'OpenCode':    ('opencode',    'opencode'),
}
NOTIFICATION_TITLES = {
    'permission_prompt':      'Needs permission',
    'elicitation_dialog':     'Needs input',
    'elicitation_url_dialog': 'Needs input',
    'agent_needs_input':      'Needs input',
}


def summarise(text: str) -> str:
    'First non-empty line of text, stripped of markdown markers and truncated'
    for line in text.splitlines():
        line = line.strip().lstrip('#>*- ').strip()
        if not line:
            continue
        return line if len(line) <= BODY_LIMIT else line[:BODY_LIMIT - 1] + '…'
    return ''


def send(app: str, key: str, title: str, body: str, urgency: str = 'normal') -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / 'lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ids = load_ids()
        cmd = [NOTIFY_SEND, '-a', app, '-u', urgency, '-p']
        if app in DESKTOP_ENTRIES:
            entry, icon = DESKTOP_ENTRIES[app]
            cmd += ['-h', f'string:desktop-entry:{entry}', '-i', icon]
        if key in ids:
            cmd += ['-r', str(ids[key])]
        result = subprocess.run([*cmd, title, body], capture_output=True, text=True, timeout=10)
        if result.returncode != 0 or not result.stdout.strip().isdigit():
            return
        ids.pop(key, None)
        ids[key] = int(result.stdout.strip())
        save_ids(ids)


def load_ids() -> dict[str, int]:
    try:
        data = json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, int)}


def save_ids(ids: dict[str, int]) -> None:
    trimmed = dict(list(ids.items())[-MAX_KEYS:])
    tmp = STATE_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(trimmed))
    tmp.replace(STATE_FILE)


def claude_hook(payload: dict[str, object]) -> None:
    event   = str(payload.get('hook_event_name', ''))
    key     = f'claude:{payload.get("session_id", "")}'
    project = Path(str(payload.get('cwd') or os.getcwd())).name
    title   = f'{CLAUDE_APP} · {project}'

    if event == 'Stop':
        # Paused while background agents/tasks run; Stop fires again when they finish.
        if payload.get('background_tasks') or payload.get('stop_hook_active'):
            return
        body = summarise(str(payload.get('last_assistant_message') or '')) or 'Finished'
        send(CLAUDE_APP, key, f'{title} · Done', body)
        return

    if event == 'StopFailure':
        body = summarise(str(payload.get('last_assistant_message') or payload.get('error') or ''))
        send(CLAUDE_APP, key, f'{title} · Error', body or 'Turn failed')
        return

    if event == 'Notification':
        label = NOTIFICATION_TITLES.get(str(payload.get('notification_type', '')))
        if label is None:
            return
        send(CLAUDE_APP, key, f'{title} · {label}', str(payload.get('message') or ''))


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == 'claude':
        try:
            payload = json.load(sys.stdin)
        except ValueError:
            return 0
        if isinstance(payload, dict):
            claude_hook(payload)
        return 0
    if len(argv) in (6, 7) and argv[1] == 'send':
        send(*argv[2:])
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except (OSError, subprocess.SubprocessError):
        sys.exit(0)
