#!/usr/bin/env python3
'''PreToolUse(Bash): block a foreground `sleep` of 30s or more anywhere in a command.

The harness only blocks commands that *start* with `sleep`; `cd x; sleep 570; cat *.status`
slipped through and stalled an orchestrator for ~10 minutes. Background commands are allowed.
'''
import json
import re
import sys

LIMIT_SECS = 30
UNIT_SECS  = {'': 1, 's': 1, 'm': 60, 'h': 3600, 'd': 86400}
SLEEP_RE   = re.compile(
    r'(?:^|[;&|(`\n]|\b(?:do|then|else|timeout\s+\S+))\s*sleep\s+(\d+(?:\.\d+)?)([smhd]?)\b'
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    tool_input = data.get('tool_input') or {}
    if tool_input.get('run_in_background'):
        return 0
    command = tool_input.get('command') or ''
    secs = max(
        (float(n) * UNIT_SECS[u] for n, u in SLEEP_RE.findall(command)),
        default=0,
    )
    if secs < LIMIT_SECS:
        return 0
    print(
        f'BLOCKED: foreground `sleep {secs:g}s` (limit {LIMIT_SECS}s). '
        'To wait for a gate, run it with `~/.claude/scripts/gate.sh` and run_in_background, '
        'then end your turn: the completion notification re-invokes you. '
        'To wait on a file or condition, use the Monitor tool with an until-loop.',
        file=sys.stderr,
    )
    return 2


if __name__ == '__main__':
    sys.exit(main())
