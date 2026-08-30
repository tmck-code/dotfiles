#!/usr/bin/env python3
'''UserPromptSubmit hook: surface matching skills when a prompt is skill-shaped.

Reads the hook payload on stdin and matches the user's prompt against a UNION of
routing tables (global + project — both optional). Every rule whose regex hits
the prompt contributes a skill + hint to a single system-reminder nudging Claude
to invoke those skills via the Skill tool before acting. Silent otherwise.

Overseer-aware: skill-overseer expresses enable/disable as `skillOverrides` in
settings.local.json. A matched skill whose effective override == 'off' is DISABLED;
the nudge marks it and instructs Claude to enable it first (overseer.py enable
<skill>) before invoking it. Enabled skills keep the plain wording, so when nothing
is disabled the message reads exactly as it did before.

Routing table resolution (UNION, not override — both contribute):
  1. ~/.claude/skill-routing.json                         (global, generic skills)
  2. $CLAUDE_PROJECT_DIR/.claude/skill-routing.json        (repo-specific skills)

Override resolution (project overrides user, per-skill — both optional/guarded):
  1. ~/.claude/settings.local.json                        (user skillOverrides)
  2. $CLAUDE_PROJECT_DIR/.claude/settings.local.json       (project skillOverrides)

Table schema:
  { "rules": [ { "skill": "<name>", "match": "<regex>",
                 "hint": "<short sentence>" }, ... ] }
'''
import json
import os
import re
import sys
from pathlib import Path


def load_rules() -> list:
    paths = [Path.home() / '.claude' / 'skill-routing.json']
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '')
    if project_dir:
        paths.append(Path(project_dir) / '.claude' / 'skill-routing.json')

    rules = []
    for path in paths:
        try:
            with path.open() as fh:
                rules.extend(json.load(fh).get('rules', []))
        except (OSError, json.JSONDecodeError, ValueError, AttributeError):
            continue  # missing/broken table -> skip it, never crash
    return rules


def load_overrides() -> dict:
    '''Effective skillOverrides map: user first, project wins per-key.'''
    paths = [Path.home() / '.claude' / 'settings.local.json']
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '')
    if project_dir:
        paths.append(Path(project_dir) / '.claude' / 'settings.local.json')

    overrides = {}
    for path in paths:
        try:
            with path.open() as fh:
                overrides.update(json.load(fh).get('skillOverrides', {}))
        except (OSError, json.JSONDecodeError, ValueError, AttributeError):
            continue  # missing/broken settings -> no overrides, never crash
    return overrides


def matched_skills(prompt: str) -> list:
    hits = []
    for rule in load_rules():
        skill = rule.get('skill')
        pattern = rule.get('match')
        if not skill or not pattern:
            continue
        try:
            if not re.search(pattern, prompt, re.IGNORECASE):
                continue
        except re.error:
            continue  # bad regex -> skip this rule
        hits.append((skill, rule.get('hint', '')))
    return hits


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    prompt = str(payload.get('prompt', ''))
    hits = matched_skills(prompt)
    if not hits:
        return 0

    overrides = load_overrides()
    overseer = 'python3 "$HOME/.claude/skills/skill-overseer/scripts/overseer.py"'

    lines = []
    for skill, hint in hits:
        suffix = f': {hint}' if hint else ''
        if overrides.get(skill) == 'off':
            lines.append(
                f'- `{skill}` (currently DISABLED){suffix} — enable it first by '
                f'running `{overseer} enable {skill}` (or invoking the '
                f'`skill-overseer` skill), THEN invoke `{skill}` via the Skill tool.'
            )
        else:
            lines.append(f'- `{skill}`{suffix}')

    context = (
        'Skill nudge (based on the shape of your prompt, not certainty). The '
        'following skill(s) look relevant:\n'
        + '\n'.join(lines)
        + '\nInvoke each matching skill via the Skill tool BEFORE acting on the '
        'prompt. These are suggestions — skip one only if it is clearly irrelevant.'
    )

    json.dump(
        {
            'hookSpecificOutput': {
                'hookEventName': 'UserPromptSubmit',
                'additionalContext': context,
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
