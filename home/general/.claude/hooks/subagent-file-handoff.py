#!/usr/bin/env python3
'''PreToolUse nudge: how a spawned subagent's result comes back.

Fires on the subagent-spawning tool (Agent / Task).

This hook used to tell the spawner to hand the subagent a report-file path and
demand it back. That instruction is now actively harmful: the harness refuses
subagent report-file writes ("Subagents should return findings as text, not write
report files"), and forensics on a real 13-subagent session measured the damage —
0/8 briefed agents returned only the path, 4/8 files were never created, 3/6
attempted writes were blocked, ~28 kB of authored analysis lost, and two wasted
re-ask round-trips that produced nothing.

Handoff is now mechanical instead: subagent-report-capture.py (SubagentStop)
writes the subagent's final message to a scratchpad file and
subagent-report-announce.py (PostToolUse) announces the path here, in the parent.
So the nudge no longer asks for a path — it reminds the spawner to READ the
announced file rather than acting on the returned message, and keeps the
sole-writer rule, which has no mechanical backstop.

Unlike nudge-delegate.py, this one does NOT stay silent for subagent-originated
calls: the convention must hold at EVERY nesting level, so nested children that
spawn their own grandchildren should be nudged too.
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
        'Subagent-handoff reminder: do NOT give this subagent a report-file path and '
        'do NOT ask it to write one — the harness refuses subagent report-file writes '
        'regardless of filename, so asking only costs a round-trip and loses the '
        'findings. Tell it to end with its findings as its FINAL MESSAGE; the capture '
        'hook writes that to a scratchpad file and the announce hook gives you the '
        'path on your next Agent/Task/TaskOutput/SendMessage call. Read that file '
        'rather than acting on the returned message — the notification channel '
        'truncates long returns and drops some entirely. Pass the same convention '
        'down to any children it spawns. '
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
