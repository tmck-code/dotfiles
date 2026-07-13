#!/usr/bin/env python3
"""Extract a draft agent-graph JSON from a Claude Code session transcript.

Reads a session `.jsonl` plus its `<session-id>/subagents/agent-*.jsonl`
(+ `.meta.json`) and emits a graph document (see REFERENCE.md) that
`build_spa.py` turns into a standalone SPA. Stdlib only, deterministic.
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime

# ---------------------------------------------------------------- helpers ---

SPAWN_TOOLS = {'Task', 'Agent'}
EDIT_TOOLS = {'Edit', 'Write', 'NotebookEdit', 'MultiEdit'}

# user-message text that is harness noise, never a real user turn
NOISE_SUBSTR = (
    'local-command-caveat', 'local-command-stdout', 'local-command-stderr',
    'system-reminder', 'task-notification', '[Request interrupted',
    'Base directory for this skill:',
)
# slash commands whose invocation is noise (not a real user request)
NOISE_COMMANDS = {'/model', '/login', '/logout', '/clear', '/config', '/compact'}


def err(msg):
    print(f'extract: {msg}', file=sys.stderr)


def die(msg, code=1):
    err(msg)
    sys.exit(code)


def default_project_dir():
    """Derive the transcript project dir from $PWD (/ -> -)."""
    enc = os.getcwd().replace('/', '-')
    for base in ('.claude.personal', '.claude'):
        cand = os.path.join(os.path.expanduser('~'), base, 'projects', enc)
        if os.path.isdir(cand):
            return cand
    # fall back to the personal path even if missing (clearer error later)
    return os.path.join(os.path.expanduser('~'), '.claude.personal', 'projects', enc)


def load_jsonl(path):
    out = []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def blocks(entry):
    c = entry.get('message', {}).get('content')
    return c if isinstance(c, list) else []


def text_of(entry):
    """Concatenated text of a message (string content or text blocks)."""
    c = entry.get('message', {}).get('content')
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return '\n'.join(b.get('text', '') for b in c if b.get('type') == 'text')
    return ''


def trunc(s, n):
    s = ' '.join((s or '').split())
    return s if len(s) <= n else s[: n - 1].rstrip() + '…'


def iso(ts):
    """Normalise a timestamp to ...Z ISO (best effort)."""
    return ts


def entry_times(entries):
    ts = [e.get('timestamp') for e in entries if e.get('timestamp')]
    ts.sort()
    return (ts[0], ts[-1]) if ts else (None, None)


def command_text(raw):
    """Turn a `<command-name>/x</command-name><command-args>y</command-args>`
    user message into "/x y", or return None if it is a noise command."""
    if '<command-name>' not in raw:
        return None
    name = re.search(r'<command-name>(.*?)</command-name>', raw, re.S)
    args = re.search(r'<command-args>(.*?)</command-args>', raw, re.S)
    if not name:
        return None
    nm = name.group(1).strip()
    if nm in NOISE_COMMANDS:
        return None
    ag = (args.group(1).strip() if args else '')
    return f'{nm} {ag}'.strip()


def real_user_text(entry):
    """Return a cleaned real user message string, or None if it is noise."""
    raw = text_of(entry)
    if not raw.strip():
        return None
    cmd = command_text(raw)
    if cmd is not None:
        return cmd
    if '<command-name>' in raw:  # a noise command (model/login/...)
        return None
    for sub in NOISE_SUBSTR:
        if sub in raw:
            return None
    return raw.strip()


# --------------------------------------------------------------- counting ---

def count_tools(entries):
    counts = {'edits': 0, 'bash': 0, 'reads': 0, 'spawns': 0}
    skills = []
    for e in entries:
        for b in blocks(e):
            if b.get('type') != 'tool_use':
                continue
            name = b.get('name', '')
            inp = b.get('input', {}) or {}
            if name in EDIT_TOOLS:
                counts['edits'] += 1
            elif name == 'Bash':
                counts['bash'] += 1
            elif name == 'Read':
                counts['reads'] += 1
                fp = inp.get('file_path', '') or ''
                m = re.search(r'skills/([^/]+)/SKILL\.md$', fp)
                if m:
                    skills.append(m.group(1))
            elif name in SPAWN_TOOLS:
                counts['spawns'] += 1
            elif name == 'Skill':
                sk = inp.get('skill') or inp.get('name')
                if sk:
                    skills.append(sk)
    # dedupe skills, preserve first-seen order
    seen, uniq = set(), []
    for s in skills:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return counts, uniq


def last_assistant_text(entries):
    for e in reversed(entries):
        if e.get('type') == 'assistant':
            t = '\n'.join(b.get('text', '') for b in blocks(e) if b.get('type') == 'text')
            if t.strip():
                return t.strip()
    return ''


def status_of(final_text):
    low = final_text.lower()
    if 'session limit' in low or 'usage limit' in low or 'limit window' in low:
        return 'cutoff'
    if 'api error' in low or 'connection closed' in low or 'connection error' in low:
        return 'dropped'
    if 'no tools needed' in low or 'harness fault' in low:
        return 'fault'
    return 'ok'


def work_of(agent_type, counts, title, prompt):
    if counts['spawns'] > 0:
        return 'orchestration'
    if agent_type == 'gates':
        return 'testing'
    if counts['edits'] == 0 and counts['reads'] > 0:
        return 'research'
    blob = f'{title} {prompt}'.lower()
    if 'docs' in blob or 'documentation' in blob or 'whereis' in blob:
        return 'docs'
    return 'implementation'


# -------------------------------------------------------------- discovery ---

def spawn_uses(entries):
    """All Task/Agent tool_use blocks in a transcript: id -> {input}."""
    out = {}
    for e in entries:
        for b in blocks(e):
            if b.get('type') == 'tool_use' and b.get('name') in SPAWN_TOOLS:
                out[b.get('id')] = b.get('input', {}) or {}
    return out


@dataclass
class Filters:
    'Session-listing filters; all optional, AND-composed.'
    grep:  list = field(default_factory=list)   # lowercased words, all must appear
    tool:  str  = None                          # tool/skill/command name (exact, ci)
    since: float = None                          # keep mtime >= since (unix ts)
    until: float = None                          # keep mtime <= until (unix ts)


def iter_project_dirs():
    'Yield every transcript project dir under the personal + fallback roots.'
    for base in ('.claude.personal', '.claude'):
        root = os.path.join(os.path.expanduser('~'), base, 'projects')
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            cand = os.path.join(root, name)
            if os.path.isdir(cand):
                yield cand


def decode_project_dir(project_dir):
    'Decode an encoded project dir name back to its cwd (lossy on hyphens).'
    return os.path.basename(project_dir).replace('-', '/')


def parse_time_bound(s):
    'Parse an ISO date/datetime or a relative form (2d, 12h, 30m) to a unix ts.'
    s = s.strip()
    m = re.fullmatch(r'(\d+)\s*([smhdw])', s, re.I)
    if m:
        secs = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}[m.group(2).lower()]
        return time.time() - int(m.group(1)) * secs
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        die(f'unrecognised time {s!r} (use an ISO date/datetime or forms like 2d, 12h)')


def _tool_use_matches(block, name_lc):
    'A tool_use block matching --tool by tool name or (for Skill) its skill arg.'
    if block.get('name', '').lower() == name_lc:
        return True
    if block.get('name') == 'Skill':
        inp = block.get('input') or {}
        sk = (inp.get('skill') or inp.get('name') or '').lower()
        return sk == name_lc
    return False


def _command_matches(raw, name_lc):
    'A slash-command / plugin-skill user turn matching --tool by its name.'
    target = name_lc.lstrip('/')
    for tag in ('command-name', 'command-message'):
        m = re.search(rf'<{tag}>(.*?)</{tag}>', raw, re.S)
        if m and m.group(1).strip().lstrip('/').lower() == target:
            return True
    return False


def scan_session(path, filters):
    'Lazy pass; return a row if the session has spawns and passes grep/tool.'
    spawns = 0
    first_user = ''
    grep_need = set(filters.grep)
    want_grep = bool(filters.grep)
    want_tool = filters.tool is not None
    tool_lc = (filters.tool or '').lower()
    tool_hit = not want_tool
    try:
        fh = open(path, encoding='utf-8')
    except OSError:
        return None
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = e.get('message', {}).get('content')
            if isinstance(content, list):
                for b in content:
                    if not isinstance(b, dict) or b.get('type') != 'tool_use':
                        continue
                    if b.get('name') in SPAWN_TOOLS:
                        spawns += 1
                    if want_tool and not tool_hit and _tool_use_matches(b, tool_lc):
                        tool_hit = True
            if e.get('type') != 'user':
                continue
            if not first_user:
                t = real_user_text(e)
                if t:
                    first_user = t
            if want_grep and grep_need:
                hay = text_of(e).lower()
                grep_need -= {w for w in grep_need if w in hay}
            if want_tool and not tool_hit and isinstance(content, str):
                tool_hit = _command_matches(content, tool_lc)
    if spawns == 0:
        return None
    if want_grep and grep_need:
        return None
    if not tool_hit:
        return None
    st = os.stat(path)
    return {
        'id': os.path.basename(path)[:-6],
        'mtime': st.st_mtime,
        'size': st.st_size,
        'spawns': spawns,
        'first': first_user,
    }


def collect_rows(project_dirs, filters, repo_substr, show_repo):
    'Scan every session under the given project dirs, applying all filters.'
    rows = []
    for pdir in project_dirs:
        if not os.path.isdir(pdir):
            die(f'project dir not found: {pdir}')
        repo = decode_project_dir(pdir)
        if repo_substr and repo_substr.lower() not in repo.lower():
            continue
        for fn in sorted(os.listdir(pdir)):
            if not fn.endswith('.jsonl'):
                continue
            path = os.path.join(pdir, fn)
            try:
                mtime = os.stat(path).st_mtime
            except OSError:
                continue
            if filters.since is not None and mtime < filters.since:
                continue
            if filters.until is not None and mtime > filters.until:
                continue
            row = scan_session(path, filters)
            if row is None:
                continue
            if show_repo:
                row['repo'] = repo
            rows.append(row)
    rows.sort(key=lambda r: r['mtime'], reverse=True)
    return rows


def cmd_list(project_dirs, filters, repo_substr, show_repo, label):
    rows = collect_rows(project_dirs, filters, repo_substr, show_repo)
    if not rows:
        print(f'No sessions with agent spawns {label}')
        return
    print(f'Sessions with agent/task spawns {label} (newest first):\n')
    for r in rows:
        when = datetime.fromtimestamp(r['mtime']).strftime('%Y-%m-%d %H:%M')
        size = f'{r["size"] / 1024:.0f}K'
        line = f'  {r["id"]}  {when}  {size:>6}  {r["spawns"]:>2} spawns'
        if show_repo:
            line += f'  [{r["repo"]}]'
        print(line)
        if r['first']:
            print(f'      {trunc(r["first"], 96)}')
    print()


# ---------------------------------------------------------------- extract ---

def build_graph(project_dir, session_id):
    main_path = os.path.join(project_dir, f'{session_id}.jsonl')
    if not os.path.isfile(main_path):
        die(f'session transcript not found: {main_path}')
    sub_dir = os.path.join(project_dir, session_id, 'subagents')

    main_entries = load_jsonl(main_path)
    m_start, m_end = entry_times(main_entries)

    # spawn tool_use across ALL transcripts: toolUseId -> input (model/desc/prompt)
    all_spawns = dict(spawn_uses(main_entries))

    # gather subagent transcripts + metas
    subs = []  # (id, entries, meta)
    if os.path.isdir(sub_dir):
        for fn in sorted(os.listdir(sub_dir)):
            if not (fn.startswith('agent-') and fn.endswith('.jsonl')):
                continue
            aid = fn[len('agent-'):-len('.jsonl')]
            entries = load_jsonl(os.path.join(sub_dir, fn))
            meta = {}
            mp = os.path.join(sub_dir, f'agent-{aid}.meta.json')
            if os.path.isfile(mp):
                try:
                    meta = json.load(open(mp, encoding='utf-8'))
                except (OSError, json.JSONDecodeError):
                    meta = {}
            all_spawns.update(spawn_uses(entries))
            subs.append((aid, entries, meta))
    else:
        err(f'no subagents dir at {sub_dir}; emitting main-only graph')

    known_ids = {'main'} | {aid for aid, _, _ in subs}

    # ---- first real user message (main) ----
    first_user = ''
    for e in main_entries:
        if e.get('type') == 'user':
            t = real_user_text(e)
            if t:
                first_user = t
                break

    agents = []

    # ---- root / main ----
    main_counts, main_skills = count_tools(main_entries)
    main_final = last_assistant_text(main_entries)
    agents.append({
        'id': 'main',
        'parent': None,
        'type': 'main',
        'model': None,
        'title': trunc(first_user, 60) or 'Main thread',
        'start': m_start,
        'end': m_end,
        'status': 'ok',
        'work': 'orchestration',
        'skills': main_skills,
        'counts': main_counts,
        'brief': trunc(first_user, 350),
        'outcome': trunc(main_final, 350),
    })

    # ---- subagents ----
    for aid, entries, meta in subs:
        s_start, s_end = entry_times(entries)
        counts, skills = count_tools(entries)
        final = last_assistant_text(entries)
        atype = meta.get('agentType') or 'unknown'
        tool_use_id = meta.get('toolUseId')
        spawn_inp = all_spawns.get(tool_use_id, {})
        model = spawn_inp.get('model')
        title = meta.get('description') or spawn_inp.get('description') or aid
        prompt = spawn_inp.get('prompt', '')
        # first user message of the subagent == its brief/prompt
        first_msg = ''
        for e in entries:
            if e.get('type') == 'user':
                t = text_of(e)
                if t.strip():
                    first_msg = t.strip()
                    break
        brief_src = prompt or first_msg

        # ---- parentage ----
        raw_parent = meta.get('parentAgentId')
        depth = meta.get('spawnDepth')
        parent_guessed = False
        if raw_parent and raw_parent in known_ids:
            parent = raw_parent
        elif raw_parent:
            # ghost parent: try to attach to nearest resolvable ancestor, else root
            parent = 'main'
            parent_guessed = True
        elif depth == 1 or depth is None:
            parent = 'main'
        else:
            parent = 'main'
            parent_guessed = True

        status = status_of(final)
        work = work_of(atype, counts, title, brief_src)

        agent = {
            'id': aid,
            'parent': parent,
            'type': atype,
            'model': model,
            'title': trunc(title, 80),
            'start': s_start,
            'end': s_end,
            'status': status,
            'work': work,
            'skills': skills,
            'counts': counts,
            'brief': trunc(brief_src, 350),
            'outcome': trunc(final, 350),
        }
        if parent_guessed:
            agent['parentGuessed'] = True
        agents.append(agent)

    # ---- markers from the MAIN transcript ----
    markers = []
    for e in main_entries:
        if e.get('type') == 'user':
            t = real_user_text(e)
            if t:
                markers.append({'at': e.get('timestamp'), 'label': trunc(t, 140)})
        elif e.get('type') == 'assistant':
            for b in blocks(e):
                if b.get('type') == 'tool_use' and b.get('name') == 'Bash':
                    cmd = (b.get('input', {}) or {}).get('command', '')
                    label = git_label(cmd)
                    if label:
                        markers.append({'at': e.get('timestamp'), 'label': label})
    markers = [m for m in markers if m.get('at')]
    markers.sort(key=lambda m: m['at'])

    graph = {
        'draft': True,
        'session': {
            'id': session_id,
            'startedAt': m_start,
            'endedAt': m_end,
            'firstUserMessage': first_user,
        },
        'eyebrow': f'session {session_id[:8]}',
        'title': trunc(first_user, 90) or f'Session {session_id[:8]}',
        'subtitle': '',
        'footer': '',
        'respawnOf': None,
        'groups': [],
        'extraStats': [],
        'agents': agents,
        'markers': markers,
    }
    return graph


def git_label(cmd):
    if 'git commit' in cmd:
        m = re.search(r'-m\s+["\']?(?:\$\(cat <<[\'"]?EOF[\'"]?\s*\n)?(.+)', cmd)
        if m:
            first = m.group(1).splitlines()[0].strip().strip('"\'')
            first = first.replace('EOF', '').strip()
            if first:
                return f'Committed: {trunc(first, 110)}'
        return 'git commit'
    if 'git push' in cmd:
        m = re.search(r'git push\s+(\S+)\s+(\S+)', cmd)
        if m:
            return f'Pushed to {m.group(1)}/{m.group(2)}'
        return 'git push'
    return None


# ------------------------------------------------------------------- main ---

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('session', nargs='?', help='session id to extract')
    ap.add_argument('--list', action='store_true', help='list sessions with spawns')
    ap.add_argument('--project-dir', help='transcript project dir (default: derive from $PWD)')
    ap.add_argument('-o', '--output', help='output path (default: stdout)')
    # --list filter flags (AND-composed)
    ap.add_argument('--all-projects', action='store_true',
                    help='list across every project dir, not just the cwd one')
    ap.add_argument('--repo', metavar='SUBSTR',
                    help='with --all-projects, keep repos whose path contains SUBSTR (ci)')
    ap.add_argument('--grep', action='append', metavar='WORDS',
                    help='keep sessions whose user turns contain all these words (ci); repeatable')
    ap.add_argument('--tool', metavar='NAME',
                    help='keep sessions that invoked this tool / skill / slash-command (ci)')
    ap.add_argument('--since', metavar='WHEN', help='keep sessions modified since (ISO date/time or 2d, 12h)')
    ap.add_argument('--until', metavar='WHEN', help='keep sessions modified before (ISO date/time or 1d)')
    args = ap.parse_args()

    project_dir = args.project_dir or default_project_dir()

    if args.list:
        grep_words = [w.lower() for g in (args.grep or []) for w in g.split()]
        filters = Filters(
            grep  = grep_words,
            tool  = args.tool,
            since = parse_time_bound(args.since) if args.since else None,
            until = parse_time_bound(args.until) if args.until else None,
        )
        if args.all_projects:
            cmd_list(list(iter_project_dirs()), filters, args.repo, True, 'across all projects')
        else:
            if args.repo:
                err('--repo only applies with --all-projects; ignoring it')
            cmd_list([project_dir], filters, None, False, f'in {project_dir}')
        return
    if not args.session:
        die('provide a session id, or use --list')

    graph = build_graph(project_dir, args.session)
    out = json.dumps(graph, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as fh:
            fh.write(out + '\n')
        err(f'wrote {args.output}  ({len(graph["agents"])} agents, {len(graph["markers"])} markers)')
    else:
        print(out)


if __name__ == '__main__':
    main()
