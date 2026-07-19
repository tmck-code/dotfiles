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
        'Subagent-handoff reminder: report-file capture now happens automatically — '
        'the SubagentStop hook mechanically writes this subagent\'s final message to '
        'a scratchpad report file regardless of cooperation, and announces its path '
        'via additionalContext after the agent stops. Look for that notice and READ '
        'the file instead of acting on the returned text; no need to pre-arrange a '
        'report-file path yourself. '
        'Sole-writer reminder: if this agent EDITS files, tell it that it is the only '
        'writer of the files in its brief and MUST NOT fork a child that edits those '
        'same files — a nested same-file fork is the classic silent lost-update race. '
        'Parallel children write to SEPARATE files (or their own git worktree) and the '
        'parent integrates; scope throwaway scratch to a per-agent subdir, never a '
        'shared flat namespace.'
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
