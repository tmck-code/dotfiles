#!/usr/bin/env python3
'''PreToolUse nudge engine: keep heavy work off the main thread.

Data-driven successor to per-repo nudge hooks. When the MAIN thread makes a tool
call that a routing table says should be delegated, inject a non-blocking reminder
to hand it to a subagent (or, for size-gated Read rules, hard-block it). The call
is otherwise allowed — most rules only nudge.

Routing table resolution (project overrides user):
  1. $CLAUDE_PROJECT_DIR/.claude/delegate-routing.json   (if present)
  2. ~/.claude/delegate-routing.json                      (fallback default)

Table schema:
  { "rules": [
      { "tool": "Bash", "match": "<regex>", "agent": "<name?>", "hint": "..." },
      { "tool": "Read", "maxLines": 100, "maxBytes": 20000,
        "action": "deny", "agent": "<name?>", "hint": "..." },
      ...
  ] }
  - "tool" defaults to "Bash". Bash matches tool_input.command; Edit/Write match
    tool_input.file_path via "match" (regex).
  - Read rules are size-gated, not regex: they fire when the slice the call would
    pull into context is >= maxLines OR >= maxBytes (either arm; both optional).
  - "action" (Read only) is "nudge" (default) or "deny". "deny" hard-blocks the
    read and returns the hint to the model so it delegates instead.
  - "agent" is optional — when set, the message names it.

It must NOT nag subagents: they legitimately run gates, edits, and big reads.
Claude Code populates agent_id/agent_type in the hook stdin ONLY for
subagent-originated tool calls, so their presence means "not the main thread"
-> stay silent.
'''
import json
import os
import re
import sys
from pathlib import Path

# Read's default page size when no explicit limit is given.
READ_DEFAULT_LIMIT = 2000

# Extensions where a line/byte count is meaningless (binary, or rendered
# specially by Read). Size-gating these would be noise.
SIZE_SKIP_SUFFIXES = frozenset({
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.ico', '.tiff',
    '.pdf', '.ipynb',
})


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


def read_slice_size(tool_input: dict):
    '''Measure the (lines, bytes) the Read call would actually pull into context.

    Honors offset/limit exactly as Read does, so a targeted small read of a big
    file is measured small. Returns None when the file can't be measured or is a
    binary/rendered type we don't size-gate.
    '''
    path = tool_input.get('file_path', '')
    if not path:
        return None
    if Path(path).suffix.lower() in SIZE_SKIP_SUFFIXES:
        return None
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None  # missing/unreadable -> nothing to gate, let it through

    lines = data.split(b'\n')
    offset = tool_input.get('offset')
    limit = tool_input.get('limit')
    start = max(0, int(offset) - 1) if offset else 0
    count = int(limit) if limit else READ_DEFAULT_LIMIT
    chunk = lines[start:start + count]

    read_lines = len(chunk)
    # +1 per line approximates the stripped newline; close enough for a threshold.
    read_bytes = sum(len(line) + 1 for line in chunk)
    return read_lines, read_bytes


def emit(nudge: str, agent: str, deny: bool) -> None:
    target = f' Hand it to the `{agent}` subagent.' if agent else ''
    if deny:
        reason = (
            f'Blocked by context-discipline policy: {nudge}.{target} '
            'Delegate this to a subagent that reads and summarises it, rather '
            'than pulling the whole file onto the main thread.'
        )
        out = {
            'hookSpecificOutput': {
                'hookEventName':           'PreToolUse',
                'permissionDecision':      'deny',
                'permissionDecisionReason': reason,
            }
        }
    else:
        context = (
            f'Context-discipline reminder: {nudge}.{target} '
            'Unless this is a throwaway one-off check, delegate it rather than '
            'doing it on the main thread.'
        )
        out = {
            'hookSpecificOutput': {
                'hookEventName':      'PreToolUse',
                'permissionDecision': 'allow',
                'additionalContext':  context,
            }
        }
    json.dump(out, sys.stdout)


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

        # Size-gated Read rule: fire if EITHER arm is exceeded (OR).
        if tool_name == 'Read' and ('maxLines' in rule or 'maxBytes' in rule):
            size = read_slice_size(tool_input)
            if size is None:
                continue
            read_lines, read_bytes = size
            max_lines = rule.get('maxLines')
            max_bytes = rule.get('maxBytes')
            over_lines = max_lines is not None and read_lines >= max_lines
            over_bytes = max_bytes is not None and read_bytes >= max_bytes
            if not (over_lines or over_bytes):
                continue
            hint = rule.get(
                'hint',
                f'this read pulls {read_lines} lines / {read_bytes} bytes onto '
                'the main thread',
            )
            emit(hint, rule.get('agent'), deny=rule.get('action') == 'deny')
            return 0

        # Regex-matched Bash/Edit/Write rule (nudge only).
        subject = subject_for(tool_name, tool_input)
        if not subject:
            continue
        try:
            if not re.search(rule['match'], subject):
                continue
        except (re.error, KeyError):
            continue

        emit(rule.get('hint', 'delegate this off the main thread to a subagent'),
             rule.get('agent'), deny=False)
        return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())
