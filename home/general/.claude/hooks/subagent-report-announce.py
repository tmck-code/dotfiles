#!/usr/bin/env python3
'''PostToolUse companion: tell the PARENT where the captured reports landed.

subagent-report-capture.py (SubagentStop) writes each subagent's final message to
a scratchpad file, but it cannot tell the parent about it: SubagentStop's
`hookSpecificOutput.additionalContext` is delivered to the subagent's own context.
PostToolUse, by contrast, runs in the parent session and its additionalContext
does reach the parent - so the capture hook drops a breadcrumb and this hook
flushes it into the coordinator's context.

Flush semantics, and why it is not keyed on this call's tool_use_id: in practice
most spawns are ASYNC. The Agent tool_result returns a "launched successfully"
stub immediately, so PostToolUse for a given spawn fires long BEFORE that
subagent finishes - its own breadcrumb cannot exist yet. Instead we drain every
pending breadcrumb for the session on each matched call. The coordinator learns
about a finished agent at its next Agent/Task/TaskOutput/SendMessage call, which
in a delegating session is almost immediately after the task notification.

Consequence to be aware of: if a coordinator receives a notification and then
makes none of those calls, the announcement waits. The report file is written
either way - the path is deterministic, so nothing is ever lost, only announced
late.

It must NEVER block: any parse error or I/O hiccup -> exit 0 cleanly.
'''
import json
import os
import sys


MATCHED_TOOLS = ('Agent', 'Task', 'TaskOutput', 'SendMessage')


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, OSError):
        return 0  # never block on a parse hiccup

    if data.get('tool_name', '') not in MATCHED_TOOLS:
        return 0

    session_id = data.get('session_id')
    if not session_id:
        return 0

    crumb_dir = f'/tmp/claude-handoff-{session_id}'
    try:
        crumbs = sorted(
            (os.path.join(crumb_dir, name) for name in os.listdir(crumb_dir)),
            key=os.path.getmtime,
        )
    except OSError:
        return 0  # no pending captures

    captured = []
    for crumb_path in crumbs:
        try:
            with open(crumb_path) as f:
                crumb = json.load(f)
        except (OSError, json.JSONDecodeError, ValueError):
            crumb = None
        try:
            os.unlink(crumb_path)  # announce once, never twice
        except OSError:
            pass
        if not isinstance(crumb, dict) or not crumb.get('report_path'):
            continue
        if not os.path.exists(crumb['report_path']):
            continue
        captured.append(crumb)

    if not captured:
        return 0

    lines = [
        'Subagent reports captured mechanically (the subagent did not have to '
        'cooperate, and no Write tool call was involved). READ these files rather '
        'than relying on the returned message - each holds the agent\'s full final '
        'text, which the notification channel routinely truncates or drops:',
    ]
    for crumb in captured:
        label = crumb.get('description') or crumb.get('agent_type') or 'subagent'
        lines.append(
            f'- {crumb["report_path"]}  ({crumb.get("agent_type", "agent")}: {label})'
        )

    try:
        json.dump(
            {
                'hookSpecificOutput': {
                    'hookEventName':     'PostToolUse',
                    'additionalContext': '\n'.join(lines),
                }
            },
            sys.stdout,
        )
    except (OSError, ValueError):
        return 0  # emitting failed -> still never block

    return 0


if __name__ == '__main__':
    sys.exit(main())
