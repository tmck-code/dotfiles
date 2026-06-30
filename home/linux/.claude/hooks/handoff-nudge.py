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
    'returned diff. Having the research in context now is NOT a license to '
    'implement inline; that is the exact rationalization to resist. Only an '
    'isolated one-line fix you did not just plan or research via a subagent '
    'belongs on the main thread.'
)


def main() -> int:
    try:
        json.load(sys.stdin)  # parsed for validity; we don't branch on contents
    except (json.JSONDecodeError, ValueError, OSError):
        return 0  # never block on a parse hiccup

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
