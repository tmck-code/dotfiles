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
import re
import sys
from pathlib import Path

FABLE_RE = re.compile(r'fable', re.IGNORECASE)

# Fallback settings.json to consult when the hook input carries no top-level
# "model" field — this is where the main/session model is configured.
SETTINGS_PATH = Path('/Users/tomm/.claude.personal/settings.json')


def deny(reason: str) -> None:
    json.dump(
        {
            'hookSpecificOutput': {
                'hookEventName':            'PreToolUse',
                'permissionDecision':       'deny',
                'permissionDecisionReason': reason,
            }
        },
        sys.stdout,
    )


def main_model_is_fable(data: dict) -> bool:
    '''Fail closed: any error resolving the main model is treated as fable.'''
    top_level_model = data.get('model')
    if top_level_model:
        return bool(FABLE_RE.search(top_level_model))
    try:
        settings = json.loads(SETTINGS_PATH.read_text())
        return bool(FABLE_RE.search(settings.get('model', '')))
    except Exception:
        return True  # fail closed


def agent_pinned_model(cwd: str, subagent_type: str):
    '''Return the pinned `model:` frontmatter value for a named agent type, if any.'''
    candidates = []
    if cwd:
        candidates.append(Path(cwd) / '.claude' / 'agents' / f'{subagent_type}.md')
    candidates.append(
        Path('/Users/tomm/.claude.personal/agents') / f'{subagent_type}.md'
    )
    for path in candidates:
        try:
            text = path.read_text()
        except OSError:
            continue
        if not text.startswith('---'):
            continue
        end = text.find('\n---', 3)
        frontmatter = text[3:end] if end != -1 else text[3:]
        match = re.search(r'^model:\s*(\S+)', frontmatter, re.MULTILINE)
        if match:
            return match.group(1)
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # never block on a parse hiccup

    if data.get('tool_name', '') not in ('Agent', 'Task'):
        return 0

    tool_input = data.get('tool_input') or {}
    requested_model = tool_input.get('model', '')
    subagent_type = tool_input.get('subagent_type', '')

    if requested_model and FABLE_RE.search(requested_model):
        deny(
            "fable is blocked for subagents; retry with model 'opus', 'sonnet', "
            "or 'haiku'."
        )
        return 0

    if main_model_is_fable(data):
        if subagent_type == 'fork':
            deny(
                'forks inherit the parent (fable) main model and ignore model '
                "overrides; spawn a non-fork agent with an explicit cheaper "
                "model ('opus', 'sonnet', or 'haiku') instead."
            )
            return 0

        if not requested_model:
            pinned = agent_pinned_model(data.get('cwd', ''), subagent_type)
            if not (pinned and not FABLE_RE.search(pinned)):
                deny(
                    'this spawn would inherit the fable main model; retry with '
                    "an explicit model ('opus', 'sonnet', or 'haiku')."
                )
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
