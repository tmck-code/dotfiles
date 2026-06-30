#!/usr/bin/env python3
'''PreToolUse nudge engine: keep heavy work off the main thread.

Data-driven successor to per-repo nudge hooks. When the MAIN thread makes a tool
call that a routing table says should be delegated, inject a non-blocking reminder
to hand it to a subagent. The call is still allowed — this only nudges.

Routing table resolution (project overrides user):
  1. $CLAUDE_PROJECT_DIR/.claude/delegate-routing.json   (if present)
  2. ~/.claude/delegate-routing.json                      (fallback default)

Table schema:
  { "rules": [ { "tool": "Bash", "match": "<regex>",
                 "agent": "<optional name>", "hint": "<sentence>" }, ... ] }
  - "tool" defaults to "Bash"; Bash matches tool_input.command, Edit/Write match
    tool_input.file_path.
  - "agent" is optional — when set, the nudge names it; when absent, the nudge just
    says to delegate off the main thread.

It must NOT nag subagents: they legitimately run gates and edits. Claude Code
populates agent_id/agent_type in the hook stdin ONLY for subagent-originated tool
calls, so their presence means "not the main thread" -> stay silent.
'''
import json
import os
import re
import sys
from pathlib import Path


def load_rules() -> list:
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '')
    candidates = []
    if project_dir:
        candidates.append(Path(project_dir) / '.claude' / 'delegate-routing.json')
    candidates.append(Path.home() / '.claude' / 'delegate-routing.json')

    for path in candidates:
        try:
            with path.open() as fh:
                return json.load(fh).get('rules', [])
        except (OSError, json.JSONDecodeError, ValueError, AttributeError):
            continue  # project table absent/broken -> fall through to user default
    return []


def subject_for(tool_name: str, tool_input: dict) -> str:
    if tool_name == 'Bash':
        return tool_input.get('command', '')
    if tool_name in ('Edit', 'Write'):
        return tool_input.get('file_path', '')
    return ''


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # never block on a parse hiccup

    # Subagent-originated call -> these fields are present -> stay silent.
    if data.get('agent_id') or data.get('agent_type'):
        return 0

    tool_name = data.get('tool_name', '')
    tool_input = data.get('tool_input') or {}

    for rule in load_rules():
        if rule.get('tool', 'Bash') != tool_name:
            continue
        subject = subject_for(tool_name, tool_input)
        if not subject:
            continue
        try:
            if not re.search(rule['match'], subject):
                continue
        except (re.error, KeyError):
            continue

        hint = rule.get('hint', 'delegate this off the main thread to a subagent')
        agent = rule.get('agent')
        target = f' Hand it to the `{agent}` subagent.' if agent else ''
        nudge = (
            f'Context-discipline reminder: {hint}.{target} '
            'Unless this is a throwaway one-off check, delegate it rather than '
            'doing it on the main thread.'
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

    return 0


if __name__ == '__main__':
    sys.exit(main())
