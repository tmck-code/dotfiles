#!/usr/bin/env python3
'''SubagentStop mechanical report capture: write the subagent's report file for it.

Relying on an injected nudge asking the subagent to Write its report to a
scratchpad file is unreliable, and forensics on a real 13-subagent session put
numbers on it: 0/8 briefed agents returned only the path, 4/8 instructed files
were never created, and 3/6 attempted `.scratch/*.md` writes were refused
outright by a harness guard -

    Subagents should return findings as text, not write report files.
    Include this content in your final response instead.

- costing ~28 kB of authored analysis. Some agent types (e.g. Explore, gates)
have no Write tool at all, so cooperation is not even possible for them.

This hook captures the report mechanically, from the harness side, with no
dependence on subagent cooperation and no Write tool call to refuse.
SubagentStop's payload already carries the subagent's full final text in
`last_assistant_message` - no transcript parsing needed. We write that text to a
deterministic scratchpad path and leave a breadcrumb for the PostToolUse
companion (subagent-report-announce.py) to surface the path to the PARENT.

Why the breadcrumb, rather than telling the parent from here: SubagentStop's
`hookSpecificOutput.additionalContext` lands in the SUBAGENT's context, not the
parent's. The retired handoff-nudge.py proved that the hard way - 8/13 returns in
the forensic session opened by arguing with its coordinator-posture reminder
instead of conveying findings, and 4/13 hallucinated a nested subagent that never
existed. So this hook emits NOTHING on stdout.

Quirks (verified empirically):
  * SubagentStop fires more than once per agent. Fires with `stop_hook_active`
    truthy carry the MAIN/PARENT thread's text in `last_assistant_message`, not
    the subagent's - capture only on the falsy fire.
  * Fires with an empty `agent_type` are progress/status pings (17/27 probed
    fires), whose `last_assistant_message` is a terse status line like
    "Grepping consumers...". Capturing those writes stray report files that read
    as "my own prior message".

It must NEVER block: any parse error, missing field, or I/O hiccup -> exit 0
cleanly. We never emit a "block" decision.
'''
import json
import os
import re
import sys


def slugify(text, max_len=50):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text[:max_len].strip('-')


def read_meta(agent_transcript_path, agent_id):
    '''Load the per-subagent sidecar written at spawn time.

    Undocumented but present in v2.1.251 alongside each subagent transcript:
        .../<session_id>/subagents/agent-<agent_id>.meta.json
        {"agentType":..,"description":..,"toolUseId":..,"spawnDepth":1}

    `description` here is the real per-agent brief description; the payload's
    `background_tasks` array is parent-scoped and usually lacks it, which is why
    slugs used to degrade to a bare agent type. Treated as best-effort: an
    absent or malformed sidecar just means fewer details in the filename.
    '''
    if not agent_transcript_path:
        return {}
    meta_path = os.path.join(
        os.path.dirname(agent_transcript_path),
        f'agent-{agent_id}.meta.json',
    )
    try:
        with open(meta_path) as f:
            meta = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return {}
    return meta if isinstance(meta, dict) else {}


def description_from_payload(data, agent_id):
    '''Fallback slug source when the meta sidecar is missing.'''
    try:
        for task in data.get('background_tasks') or []:
            if task.get('id') == agent_id:
                return task.get('description')
    except (AttributeError, TypeError):
        pass
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, OSError):
        return 0  # never block on a parse hiccup

    agent_id = data.get('agent_id')
    if not agent_id:
        return 0

    # Empty agent_type -> progress ping, not a completion.
    agent_type = data.get('agent_type')
    if not agent_type:
        return 0

    # The re-fire carries the PARENT's text, not the subagent's - skip it.
    if data.get('stop_hook_active'):
        return 0

    last_message = data.get('last_assistant_message') or ''
    if not last_message.strip():
        return 0

    session_id = data.get('session_id', 'unknown')
    agent_transcript_path = data.get('agent_transcript_path')
    meta = read_meta(agent_transcript_path, agent_id)

    description = meta.get('description') or description_from_payload(data, agent_id)
    tool_use_id = meta.get('toolUseId')
    spawn_depth = meta.get('spawnDepth')

    try:
        uid = os.getuid()
        cwd = data.get('cwd', 'unknown').replace('/', '-')
        scratch_dir = f'/tmp/claude-{uid}/{cwd}/{session_id}/scratchpad/subagent-reports'
        os.makedirs(scratch_dir, exist_ok=True)
    except OSError:
        return 0  # can't make the dir -> never block

    slug = slugify(f'{agent_type}-{description}' if description else agent_type) or 'agent'
    report_path = f'{scratch_dir}/{slug}-{str(agent_id)[:8]}.md'

    lines = [
        f'**Agent type:** {agent_type}',
        f'**Agent id:** {agent_id}',
    ]
    if description:
        lines.append(f'**Description:** {description}')
    if tool_use_id:
        lines.append(f'**Spawned by tool_use:** {tool_use_id}')
    if spawn_depth is not None:
        lines.append(f'**Spawn depth:** {spawn_depth}')
    if agent_transcript_path:
        lines.append(f'**Agent transcript path:** {agent_transcript_path}')
    lines += ['', '---', '', last_message]

    try:
        with open(report_path, 'w') as f:
            f.write('\n'.join(lines))
    except OSError:
        return 0  # write failed -> never block

    # Breadcrumb for the parent-side announcer. Session-scoped dir so the
    # companion can flush every pending capture without knowing agent ids.
    try:
        crumb_dir = f'/tmp/claude-handoff-{session_id}'
        os.makedirs(crumb_dir, exist_ok=True)
        crumb = json.dumps({
            'agent_id':    agent_id,
            'agent_type':  agent_type,
            'description': description,
            'tool_use_id': tool_use_id,
            'report_path': report_path,
        })
        with open(f'{crumb_dir}/{agent_id}.json', 'w') as f:
            f.write(crumb)
    except (OSError, ValueError):
        pass  # the report file is written; a missing breadcrumb is not fatal

    # Deliberately silent: SubagentStop's additionalContext reaches the subagent,
    # not the parent, and polluting a finished agent's context does only harm.
    return 0


if __name__ == '__main__':
    sys.exit(main())
