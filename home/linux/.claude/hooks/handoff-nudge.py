#!/usr/bin/env python3
'''SubagentStop nudge: re-assert the coordinator posture at the handoff.

A subagent just returned its findings/results to the MAIN thread. That is the
exact moment the model rationalizes doing the next unit of work inline ("I already
have the context"). This hook fires on SubagentStop and injects a non-blocking
reminder that the follow-on work — writing the code, syncing docs / the whereis
map / tasks.md, etc. — is itself a delegable unit and should be routed to a
subagent, not absorbed on the main thread.

It must NEVER block: any parse error or surprise -> exit 0 cleanly. The only
output is a hookSpecificOutput.additionalContext string (the verified SubagentStop
contract); we never emit a "block" decision.
'''
import json
import sys


REMINDER = (
    'Coordinator-posture reminder: a subagent just returned. The next unit of '
    'work — writing/editing the code, syncing docs, the whereis map, tasks.md, '
    'or any follow-on edit — is itself a DELEGABLE unit. Route it to a subagent '
    '(per-file or per-component, in parallel where independent) and review the '
    'returned diff. Only an isolated one-line fix you did not just plan or '
    'research via a subagent belongs on the main thread.'
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, OSError):
        return 0  # never block on a parse hiccup

    # Only nudge when a real subagent stopped (non-empty agent_type).
    if not data.get('agent_type'):
        return 0

    # The harness re-fires SubagentStop for background tasks on every turn.
    # Throttle to once per (session, agent_id) pair so we nudge only the first time.
    import pathlib
    session_id = data.get('session_id', 'unknown')
    agent_id   = data.get('agent_id', 'unknown')
    sentinel   = pathlib.Path(f'/tmp/ss-seen-{session_id}-{agent_id}')
    if sentinel.exists():
        return 0
    sentinel.touch()

    try:
        json.dump(
            {
                'hookSpecificOutput': {
                    'hookEventName':     'SubagentStop',
                    'additionalContext': REMINDER,
                }
            },
            sys.stdout,
        )
    except (OSError, ValueError):
        return 0  # emitting failed -> still never block

    return 0


if __name__ == '__main__':
    sys.exit(main())
