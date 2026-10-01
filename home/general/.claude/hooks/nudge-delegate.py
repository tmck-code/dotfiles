#!/usr/bin/env python3
'''PreToolUse nudge engine: keep heavy work off the main thread.

Data-driven successor to per-repo nudge hooks. When a tool call matches a rule in
a routing table, inject a non-blocking reminder (or, for rules with
"action": "deny", hard-block the call and return the hint to the model).

Routing table resolution (project overrides user):
  1. $CLAUDE_PROJECT_DIR/.claude/delegate-routing.json   (if present)
  2. ~/.claude/delegate-routing.json                      (fallback default)

Caller identity:
  Claude Code sets agent_id/agent_type in the hook stdin ONLY for
  subagent-originated calls. The caller is "main" when agent_id is absent,
  otherwise the agent_type string (e.g. "orchestrator", "worker"). If agent_id
  is present but agent_type is empty, the caller is unknown and matches no rule.
  Each rule has "appliesTo": [<caller>, ...], default ["main"]. Callers not
  listed (ordinary workers, Explore, ...) are never nudged.

Table schema:
  { "rules": [
      { "tool": "Bash", "match": "<regex>", "agent": "<name?>", "hint": "...",
        "action": "nudge|deny", "appliesTo": ["main"] },
      { "tool": "Read", "maxLines": 100, "maxBytes": 20000, "action": "deny", ... },
      { "tool": "Bash", "kind": "bashRead", "maxLines": 100, "maxBytes": 20000,
        "action": "deny", ... },
      { "kind": "callBudget", "appliesTo": [...], "maxCalls": 30,
        "hint": "... {count} ..." },
  ] }
  - "tool" defaults to "Bash"; it may also be a list of tool names. Bash matches
    tool_input.command; Edit/Write match tool_input.file_path via "match" (regex).
  - Read rules are size-gated, not regex: they fire when the slice the call would
    pull into context is >= maxLines OR >= maxBytes (either arm; both optional).
  - "bashRead" rules measure what cat/head/tail/sed -n would print to the terminal
    (not piped, redirected, or heredoc writers) and fire on the same limits,
    summed over the whole command. Unparseable commands are ignored.
  - "action" is "nudge" (default) or "deny" for every rule kind.
  - "callBudget" counts every call the hook sees from the caller (no "tool"
    filter) in $CLAUDE_CONFIG_DIR|~/.claude/hooks/state/calls-<session>-<agent>.json
    and nudges once when the count reaches maxCalls and once at 2x. "{count}" in
    the hint is replaced by the count. It never stops other rules being checked.
  - "agent" is optional - when set, the message names it.
  - When several rules fire on one call, a deny wins and messages are combined.
'''
import glob
import json
import os
import re
import shlex
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

SIZE_TAIL = (
    'Delegate this to a subagent that reads and summarises it, rather '
    'than pulling the whole file onto the main thread.'
)
GENERIC_TAIL = 'Delegate this to a subagent instead.'

SEGMENT_OPERATORS = frozenset({';', ';;', '&&', '||', '&'})
PIPE_OPERATORS = frozenset({'|', '|&'})
HEREDOC_RE = re.compile(r'<<-?\s*[\'"]?([A-Za-z_][\w]*)')
SED_RANGE_RE = re.compile(r'^(\d+),(\+?)(\d+)p$')
SED_LINE_RE = re.compile(r'^(\d+)p$')


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


def caller_of(data: dict):
    '''Return "main", the subagent's agent_type, or None when unknown.'''
    if not data.get('agent_id'):
        return 'main'
    return data.get('agent_type') or None


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


# --- bashRead: measure what cat/head/tail/sed -n print to the terminal ---------

def split_segments(command: str):
    '''Tokenise into [(tokens, piped)] segments. Returns None on any parse problem.

    A segment is piped when it is followed by "|" (its stdout feeds another
    command). Heredoc bodies are skipped.
    '''
    lines = command.split('\n')
    segments = []
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        heredocs = HEREDOC_RE.findall(line)
        for delim in heredocs:
            while i < len(lines) and lines[i].strip() != delim:
                i += 1
            i += 1  # skip the delimiter line itself
        if not line.strip():
            continue
        lex = shlex.shlex(line, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        lex.commenters = ''
        try:
            tokens = list(lex)
        except ValueError:
            return None
        if any(t in ('(', ')') for t in tokens):
            return None  # subshells / substitutions: do not guess
        current = []
        for tok in tokens:
            if tok in SEGMENT_OPERATORS:
                segments.append((current, False))
                current = []
            elif tok in PIPE_OPERATORS:
                segments.append((current, True))
                current = []
            else:
                current.append(tok)
        segments.append((current, False))
    return segments


def clean_args(tokens: list):
    '''Drop redirections. Returns args, or None when stdout is not the terminal.'''
    args = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith('<<'):
            return None  # heredoc / here-string
        if tok == '<':
            i += 2  # stdin redirect: target is input, not a file to print
            continue
        if tok.startswith('>') or tok.startswith('&>'):
            if tok.startswith('>') and args and args[-1] == '2':
                args.pop()  # 2> / 2>&1: stderr only
                i += 2
                continue
            return None
        args.append(tok)
        i += 1
    return args


def count_n(args: list, default: int = 10):
    '''Parse head/tail style -n N / -nN / -N / --lines=N. Returns (n, plus, rest).'''
    n, plus, rest = default, False, []
    i = 0
    while i < len(args):
        a = args[i]
        value = None
        if a == '-n' and i + 1 < len(args):
            value = args[i + 1]
            i += 1
        elif a.startswith('--lines='):
            value = a.split('=', 1)[1]
        elif re.fullmatch(r'-n\+?\d+', a):
            value = a[2:]
        elif re.fullmatch(r'-\d+', a):
            value = a[1:]
        elif a.startswith('-') and a != '-':
            i += 1
            continue
        else:
            rest.append(a)
            i += 1
            continue
        plus = value.startswith('+')
        n = int(value.lstrip('+'))
        i += 1
    return n, plus, rest


def resolve_files(names: list, cwd: Path) -> list:
    out = []
    for name in names:
        if name == '-':
            continue
        path = Path(os.path.expanduser(name))
        if not path.is_absolute():
            path = cwd / path
        if any(c in name for c in '*?['):
            out.extend(Path(g) for g in sorted(glob.glob(str(path))))
        else:
            out.append(path)
    return out


def measure_file(path: Path, pick):
    '''(lines, bytes) of the chunk selected by pick(lines) or None.'''
    if path.suffix.lower() in SIZE_SKIP_SUFFIXES:
        return None
    try:
        lines = path.read_bytes().splitlines(keepends=True)
    except OSError:
        return None  # missing, directory, unreadable
    chunk = pick(lines)
    return len(chunk), sum(len(line) for line in chunk)


def measure_segment(args: list, cwd: Path) -> list:
    '''Return [(path, lines, bytes)] this single command would print.'''
    if not args:
        return []
    cmd = os.path.basename(args[0])
    rest = args[1:]
    if cmd == 'cat':
        names = [a for a in rest if a == '-' or not a.startswith('-')]
        pick = lambda lines: lines
    elif cmd in ('head', 'tail'):
        n, plus, names = count_n(rest)
        if cmd == 'head':
            pick = lambda lines: lines[:n]
        elif plus:
            pick = lambda lines: lines[max(0, n - 1):]
        else:
            pick = lambda lines: lines[len(lines) - n:] if n else []
    elif cmd == 'sed':
        if '-n' not in rest:
            return []
        positional = [a for a in rest if not a.startswith('-')]
        if len(positional) < 2:
            return []
        script, names = positional[0].replace(' ', ''), positional[1:]
        m = SED_RANGE_RE.match(script)
        single = SED_LINE_RE.match(script)
        if m:
            first = int(m.group(1))
            last = first + int(m.group(3)) if m.group(2) else int(m.group(3))
            pick = lambda lines: lines[max(0, first - 1):last]
        elif single:
            first = int(single.group(1))
            pick = lambda lines: lines[max(0, first - 1):first]
        else:
            return []
    else:
        return []

    results = []
    for path in resolve_files(names, cwd):
        size = measure_file(path, pick)
        if size is not None:
            results.append((path, *size))
    return results


def bash_read_size(command: str, base_cwd: Path):
    '''Measure terminal-bound file output of a Bash command.

    Returns (lines, bytes, [paths]) or None when nothing is measurable.
    '''
    try:
        segments = split_segments(command)
    except Exception:  # noqa: BLE001 - never block on a parse hiccup
        return None
    if not segments:
        return None
    cwd = base_cwd
    total_lines = total_bytes = 0
    paths = []
    for tokens, piped in segments:
        args = clean_args(tokens)
        while args and re.fullmatch(r'\w+=.*', args[0]):
            args = args[1:]  # leading VAR=value
        if args is None or not args:
            continue
        if args[0] == 'cd':
            if len(args) == 2:
                target = Path(os.path.expanduser(args[1]))
                cwd = target if target.is_absolute() else cwd / target
            continue
        if piped:
            continue
        for path, n_lines, n_bytes in measure_segment(args, cwd):
            total_lines += n_lines
            total_bytes += n_bytes
            paths.append(path)
    if not paths:
        return None
    return total_lines, total_bytes, paths


# --- callBudget ----------------------------------------------------------------

def state_path(session_id: str, agent_id: str) -> Path:
    config = os.environ.get('CLAUDE_CONFIG_DIR') or str(Path.home() / '.claude')
    safe = lambda v: re.sub(r'[^\w.-]', '_', v) or 'x'
    name = f'calls-{safe(session_id or "nosession")}-{safe(agent_id or "main")}.json'
    return Path(config) / 'hooks' / 'state' / name


def bump_counter(data: dict) -> int:
    '''Increment and return this caller's call count. Tolerates corrupt state.'''
    path = state_path(data.get('session_id', ''), data.get('agent_id', ''))
    count = 0
    try:
        count = int(json.loads(path.read_text()).get('count', 0))
    except (OSError, ValueError, AttributeError, TypeError):
        count = 0
    count += 1
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'count': count}))
    except OSError:
        pass
    return count


# --- output --------------------------------------------------------------------

def render_deny(nudge: str, agent: str, tail: str) -> str:
    target = f' Hand it to the `{agent}` subagent.' if agent else ''
    return f'Blocked by context-discipline policy: {nudge}.{target} {tail}'


def render_nudge(nudge: str, agent: str) -> str:
    target = f' Hand it to the `{agent}` subagent.' if agent else ''
    return (
        f'Context-discipline reminder: {nudge}.{target} '
        'Unless this is a throwaway one-off check, delegate it rather than '
        'doing it on the main thread.'
    )


def emit(denials: list, notes: list) -> None:
    if denials:
        out = {
            'hookSpecificOutput': {
                'hookEventName':           'PreToolUse',
                'permissionDecision':      'deny',
                'permissionDecisionReason': ' '.join(denials + notes),
            }
        }
    else:
        out = {
            'hookSpecificOutput': {
                'hookEventName':      'PreToolUse',
                'permissionDecision': 'allow',
                'additionalContext':  ' '.join(notes),
            }
        }
    json.dump(out, sys.stdout)


def tool_matches(rule: dict, tool_name: str) -> bool:
    tools = rule.get('tool', 'Bash')
    if isinstance(tools, str):
        tools = [tools]
    return tool_name in tools


def check_rule(rule: dict, tool_name: str, tool_input: dict, cwd: Path):
    '''Return (message, is_deny) when the rule fires, else None.'''
    deny = rule.get('action') == 'deny'
    agent = rule.get('agent')

    if rule.get('kind') == 'bashRead':
        size = bash_read_size(tool_input.get('command', ''), cwd)
        if size is None:
            return None
        n_lines, n_bytes, paths = size
        if not (_over(rule.get('maxLines'), n_lines) or _over(rule.get('maxBytes'), n_bytes)):
            return None
        names = ', '.join(str(p) for p in paths)
        detail = f'this command prints {n_lines} lines / {n_bytes} bytes from {names}'
        hint = rule.get(
            'hint',
            'grep for the symbol you need and read a line range, or delegate it',
        )
        nudge = f'{detail}. {hint}'
    # Size-gated Read rule: fire if EITHER arm is exceeded (OR).
    elif tool_name == 'Read' and ('maxLines' in rule or 'maxBytes' in rule):
        size = read_slice_size(tool_input)
        if size is None:
            return None
        read_lines, read_bytes = size
        if not (_over(rule.get('maxLines'), read_lines) or _over(rule.get('maxBytes'), read_bytes)):
            return None
        nudge = rule.get(
            'hint',
            f'this read pulls {read_lines} lines / {read_bytes} bytes onto '
            'the main thread',
        )
    else:
        # Regex-matched Bash/Edit/Write rule.
        subject = subject_for(tool_name, tool_input)
        if not subject:
            return None
        try:
            if not re.search(rule['match'], subject):
                return None
        except (re.error, KeyError):
            return None
        nudge = rule.get('hint', 'delegate this off the main thread to a subagent')
        if deny:
            return render_deny(nudge, agent, GENERIC_TAIL), True
        return render_nudge(nudge, agent), False

    if deny:
        return render_deny(nudge, agent, SIZE_TAIL), True
    return render_nudge(nudge, agent), False


def _over(limit, value) -> bool:
    return limit is not None and value >= limit


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # never block on a parse hiccup
    if not isinstance(data, dict):
        return 0

    caller = caller_of(data)
    if caller is None:
        return 0

    tool_name = data.get('tool_name', '')
    tool_input = data.get('tool_input') or {}
    cwd = Path(tool_input.get('cwd') or data.get('cwd') or os.getcwd())

    denials, notes = [], []
    count = None
    fired_regular = False
    for rule in load_rules():
        if not isinstance(rule, dict):
            continue
        if caller not in (rule.get('appliesTo') or ['main']):
            continue

        if rule.get('kind') == 'callBudget':
            limit = rule.get('maxCalls')
            if not isinstance(limit, int) or limit < 1:
                continue
            if count is None:
                count = bump_counter(data)
            if count in (limit, 2 * limit):
                hint = rule.get('hint', 'You have made {count} tool calls.')
                notes.append(hint.replace('{count}', str(count)))
            continue

        if fired_regular:
            continue  # first matching regular rule wins; budgets are still counted
        if not tool_matches(rule, tool_name):
            continue
        fired = check_rule(rule, tool_name, tool_input, cwd)
        if fired is None:
            continue
        fired_regular = True
        message, is_deny = fired
        (denials if is_deny else notes).append(message)

    if denials or notes:
        emit(denials, notes)
    return 0


if __name__ == '__main__':
    sys.exit(main())
