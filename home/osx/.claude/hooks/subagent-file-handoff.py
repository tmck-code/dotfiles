#!/usr/bin/env python3
'''PreToolUse nudge: sole-writer ownership boundaries for spawned subagents.

Fires on the subagent-spawning tool (Agent / Task). Report-file capture is now
handled mechanically by the SubagentStop hook (subagent-report-capture.py), which
writes the subagent's last_assistant_message to a scratchpad file regardless of
whether the subagent cooperates or even has a Write tool — so this hook no longer
needs to instruct the spawning agent to pre-arrange a report-file path. Look for
the additionalContext path notice emitted after the agent stops instead.

What this hook still does: inject a non-blocking reminder about the SOLE-WRITER
rule — if the spawned agent edits files, it must be the only writer of the files
in its brief and must not fork a child that edits those same files. That guidance
is unrelated to report capture (it is about subagents not clobbering each other's
*working* files) and remains fully relevant. The spawn is still allowed.

Unlike nudge-delegate.py, this one does NOT stay silent for subagent-originated
calls: the sole-writer convention must hold at EVERY nesting level, so nested
children that spawn their own grandchildren should be nudged too.
'''
import json
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # never block on a parse hiccup

    if data.get('tool_name', '') not in ('Agent', 'Task'):
        return 0

    nudge = (
        'Sole-writer reminder: if this agent EDITS files, it is the only writer of '
        'the files in its brief and must keep parallel children on SEPARATE files '
        '(or their own git worktree) — a nested same-file fork is the classic silent '
        'lost-update race; the parent integrates, and scratch stays in a per-agent '
        'subdir. (Report-file capture is automatic; you\'ll get the path when it stops.)'
    )
    json.dump(
        {
            'hookSpecificOutput': {
                'hookEventName':      'PreToolUse',
                'permissionDecision': 'allow',
                'additionalContext':  nudge,
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
