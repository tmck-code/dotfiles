#!/usr/bin/env python3
'''PreToolUse nudge: subagent results go through files, not return messages.

Fires on the subagent-spawning tool (Agent / Task). A subagent's returned text is
unreliable — the parent often sees only part of a long message, or none of it. So
every time an agent is spawned, inject a non-blocking reminder to hand the result
back through a uniquely-named markdown file in the scratchpad and read that file
rather than trusting the returned message. The spawn is still allowed.

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
        'Subagent-handoff reminder: returned messages are unreliable — the parent '
        'often sees only part of a long message, or none of it. In this spawn, give '
        'the subagent a uniquely-named markdown report-file path in the scratchpad '
        '(named after its task so siblings never collide), tell it to write its full '
        'report there BEFORE returning and to return only that path, then READ that '
        'file instead of acting on the returned text. Pass the same convention down '
        'to any children it spawns. '
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
