#!/usr/bin/env python3
'''SubagentStop mechanical report capture: write the subagent's report file for it.

The old approach relied on an injected PreToolUse nudge asking the SPAWNING agent
to tell the subagent to Write its report to a scratchpad file before returning.
That is unreliable: the subagent sometimes forgets, and some agent types (e.g.
Explore) have no Write tool at all, so cooperation is not even possible.

This hook instead captures the report mechanically, from the harness side, with no
dependence on subagent cooperation. SubagentStop's payload already carries the
subagent's full final text in `last_assistant_message` — no transcript parsing
needed. We write that text to a deterministic scratchpad path and tell the parent
where to find it via additionalContext.

Quirk (verified empirically): SubagentStop fires TWICE per agent. The first fire
has `stop_hook_active: false` and `last_assistant_message` is the genuine subagent
output. The second fire has `stop_hook_active: true` and `last_assistant_message`
is actually the MAIN/PARENT thread's own follow-up text, not the subagent's. We
must only capture on the first (stop_hook_active falsy) fire.

It must NEVER block: any parse error, missing field, or I/O hiccup -> exit 0
cleanly. The only output is a hookSpecificOutput.additionalContext string; we
never emit a "block" decision.
'''
import json
import os
import re
import sys


def slugify(text, max_len=50):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text[:max_len].strip('-')


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, OSError):
        return 0  # never block on a parse hiccup

    agent_id = data.get('agent_id')
    if not agent_id:
        return 0

    # The main-thread re-fire carries the PARENT's text, not the subagent's - skip it.
    if data.get('stop_hook_active'):
        return 0

    last_message = data.get('last_assistant_message', '')

    try:
        uid = os.getuid()
        cwd = data.get('cwd', 'unknown').replace('/', '-')
        session_id = data.get('session_id', 'unknown')
        scratch_dir = f'/tmp/claude-{uid}/{cwd}/{session_id}/scratchpad/subagent-reports'
        os.makedirs(scratch_dir, exist_ok=True)
    except OSError:
        return 0  # can't make the dir -> never block

    agent_type = data.get('agent_type') or 'agent'
    description = None
    try:
        for task in data.get('background_tasks') or []:
            if task.get('id') == agent_id:
                description = task.get('description')
                break
    except (AttributeError, TypeError):
        description = None

    slug = slugify(description or agent_type) or 'agent'
    agent_id_prefix = str(agent_id)[:8]
    report_path = f'{scratch_dir}/{slug}-{agent_id_prefix}.md'

    lines = [
        f'**Agent type:** {agent_type}',
        f'**Agent id:** {agent_id}',
    ]
    if description:
        lines.append(f'**Description:** {description}')
    agent_transcript_path = data.get('agent_transcript_path')
    if agent_transcript_path:
        lines.append(f'**Agent transcript path:** {agent_transcript_path}')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append(last_message)

    try:
        with open(report_path, 'w') as f:
            f.write('\n'.join(lines))
    except OSError:
        return 0  # write failed -> never block

    try:
        json.dump(
            {
                'hookSpecificOutput': {
                    'hookEventName':     'SubagentStop',
                    'additionalContext': (
                        f'Subagent report captured mechanically at {report_path}. '
                        'Read that file rather than trusting the returned message - '
                        'it always exists regardless of whether the subagent cooperated.'
                    ),
                }
            },
            sys.stdout,
        )
    except (OSError, ValueError):
        return 0  # emitting failed -> still never block

    return 0


if __name__ == '__main__':
    sys.exit(main())
