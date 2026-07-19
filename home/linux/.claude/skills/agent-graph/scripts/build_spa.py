#!/usr/bin/env python3
"""Render a graph JSON into a standalone agent-graph SPA.

Single-file mode: reads a graph document (see REFERENCE.md) and the sibling
`template.html`, substitutes the data + title, and writes a self-contained HTML.

Directory mode: pass a directory instead of a file. Globs all *.json files in
that directory (sorted), skips _meta.json (reserved for overrides), prefixes
every agent id with a per-session slug, reparents session roots under a
synthetic combined root, derives title/eyebrow/subtitle/markers from the
aggregated data, then runs the same render path. An optional _meta.json may
override title, eyebrow, subtitle, extraStats, orientation, and footer.
"""

import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, 'template.html')

_git_org_cache: dict = {}


def git_org(cwd):
    """Return the lowercased GitHub org for cwd's git remote, or None."""
    if cwd is None:
        return None
    if cwd in _git_org_cache:
        return _git_org_cache[cwd]
    result = None
    try:
        proc = subprocess.run(
            ['git', '-C', cwd, 'config', '--get', 'remote.origin.url'],
            capture_output=True, text=True, timeout=3,
        )
        url = (proc.stdout or '').strip()
        if url:
            m = re.match(r'git@github\.com:([^/]+)/', url)
            if not m:
                m = re.match(r'https?://github\.com/([^/]+)/', url)
            if m:
                result = m.group(1).lower()
    except Exception:
        pass
    _git_org_cache[cwd] = result
    return result


def die(msg):
    print(f'build_spa: {msg}', file=sys.stderr)
    sys.exit(1)


def validate(graph):
    agents = graph.get('agents')
    if not isinstance(agents, list) or not agents:
        die('graph.agents must be a non-empty array')
    roots = [a for a in agents if a.get('parent') in (None, '', 'null')]
    if len(roots) != 1:
        ids = ', '.join(a.get('id', '?') for a in roots) or '(none)'
        die(f'exactly one root (parent null) required, found {len(roots)}: {ids}')
    ids = {a.get('id') for a in agents}
    for a in agents:
        if 'id' not in a:
            die('every agent needs an id')
        p = a.get('parent')
        if p not in (None, '', 'null') and p not in ids:
            die(f'agent {a.get("id")!r} has unknown parent {p!r}')
    for g in (graph.get('groups') or []):
        for cid in g:
            if cid not in ids:
                die(f'groups references unknown agent id {cid!r}')


# ---------------------------------------------------------------------------
# helpers for dir mode
# ---------------------------------------------------------------------------

def slugify(s, index=None):
    """Lowercase, collapse non-alphanumeric runs to '-', strip edges."""
    slug = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    if not slug:
        slug = f's{index}' if index is not None else 'session'
    return slug


def clean_title(msg):
    """Derive a short readable title from a raw firstUserMessage."""
    if not msg:
        return '(session)'
    t = ' '.join(msg.split())
    m = re.match(r'^/?load skills?\s+(.+)', t, re.I)
    if m:
        t = 'Load ' + m.group(1)
    elif t.startswith('/'):
        pass  # leave slash commands as-is
    t = t.strip('"\'')
    if len(t) > 50:
        t = t[:49].rstrip() + '…'
    return t


def parse_iso(s):
    return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def fmt_iso(d):
    return d.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def _collect_timestamps(agents):
    starts, ends = [], []
    for a in agents:
        if a.get('start'):
            try:
                starts.append(parse_iso(a['start']))
            except ValueError:
                pass
        if a.get('end'):
            try:
                ends.append(parse_iso(a['end']))
            except ValueError:
                pass
    return starts, ends


def build_combined_graph(dirpath, cli_orientation, org_target='lexerdev', any_org=False):
    """Load all *.json session files from dirpath and combine into one graph."""
    all_files = sorted(
        f for f in glob.glob(os.path.join(dirpath, '*.json'))
        if os.path.basename(f) != '_meta.json'
    )
    if not all_files:
        die(f'no *.json session files found in {dirpath}')

    # --- load sessions, skip bad files ---
    sessions = []  # list of (stem, graph_dict)
    for path in all_files:
        stem = os.path.splitext(os.path.basename(path))[0]
        fname = os.path.basename(path)
        try:
            data = json.load(open(path, encoding='utf-8'))
        except (json.JSONDecodeError, OSError) as e:
            print(f'build_spa: warning: skipping {fname}: {e}', file=sys.stderr)
            continue
        if not isinstance(data.get('agents'), list):
            print(f'build_spa: warning: skipping {fname}: no agents array', file=sys.stderr)
            continue
        part_root = next(
            (a for a in data['agents'] if a.get('parent') in (None, '', 'null')),
            None,
        )
        if part_root is None:
            print(f'build_spa: warning: skipping {fname}: no root agent found', file=sys.stderr)
            continue

        # --- org filter (default ON) ---
        if not any_org:
            sess_meta = data.get('session') or {}
            recorded_org = sess_meta.get('org')
            if recorded_org:
                file_org = recorded_org.lower() if isinstance(recorded_org, str) else None
            else:
                cwd = sess_meta.get('cwd')
                file_org = git_org(cwd) if cwd else None
            target_lc = (org_target or 'lexerdev').lower()
            if file_org is None:
                print(
                    f'build_spa: skipping {fname}: org unknown',
                    file=sys.stderr,
                )
                continue
            if file_org != target_lc:
                print(
                    f"build_spa: skipping {fname}: org {file_org!r} != {target_lc!r}",
                    file=sys.stderr,
                )
                continue

        sessions.append((stem, data))

    if not sessions:
        if any_org:
            die(f'zero usable session files in {dirpath} (all skipped or invalid)')
        else:
            target_lc = (org_target or 'lexerdev').lower()
            die(
                f'no {target_lc} sessions found in {dirpath} '
                f'(use --any-org to include all)'
            )

    # --- build unique prefixes (detect slug collisions) ---
    seen_slugs: dict[str, int] = {}
    prefixes = []
    for i, (stem, _) in enumerate(sessions):
        base = slugify(stem, index=i)
        if base in seen_slugs:
            seen_slugs[base] += 1
            slug = f'{base}-{seen_slugs[base]}'
        else:
            seen_slugs[base] = 0
            slug = base
        prefixes.append(slug + '__')

    # --- prefix agents and reparent ---
    combined_agents = []
    all_starts: list[dt.datetime] = []
    all_ends: list[dt.datetime] = []

    for (stem, data), prefix in zip(sessions, prefixes):
        agents = data['agents']
        fum = (data.get('session') or {}).get('firstUserMessage')
        for a in agents:
            b = dict(a)
            b['id'] = prefix + a['id']
            raw_parent = a.get('parent')
            if raw_parent in (None, '', 'null'):
                b['parent'] = 'root'
                # derive title from firstUserMessage, fall back to existing title
                b['title'] = clean_title(fum) if fum else a.get('title', stem)
            else:
                b['parent'] = prefix + raw_parent
            if b.get('respawnOf'):
                b['respawnOf'] = prefix + b['respawnOf']
            combined_agents.append(b)

        s, e = _collect_timestamps(agents)
        all_starts.extend(s)
        all_ends.extend(e)

    # --- synthetic root ---
    span_start = min(all_starts) if all_starts else dt.datetime.now(dt.timezone.utc)
    span_end = max(all_ends) if all_ends else span_start
    n_sessions = len(sessions)

    root_agent = {
        'id': 'root',
        'parent': None,
        'type': 'main',
        'work': 'orchestration',
        'title': f'{n_sessions} sessions',
        'start': fmt_iso(span_start),
        'end': fmt_iso(span_end),
        'counts': {'spawns': n_sessions},
    }
    all_agents = [root_agent] + combined_agents

    # --- extraStats ---
    non_root = [a for a in all_agents if a['id'] != 'root']
    tot_edits = sum(a.get('counts', {}).get('edits', 0) for a in non_root)
    tot_bash = sum(a.get('counts', {}).get('bash', 0) for a in non_root)
    n_agents = len(non_root)
    extra_stats = [
        [str(n_sessions), 'sessions'],
        [str(n_agents), 'agents'],
        [str(tot_edits), 'file edits'],
        [str(tot_bash), 'shell runs'],
    ]

    # --- header text ---
    dirname = os.path.basename(os.path.abspath(dirpath))
    d0 = span_start.astimezone(dt.timezone.utc).strftime('%Y-%m-%d')
    d1 = span_end.astimezone(dt.timezone.utc).strftime('%Y-%m-%d')
    title = f'{n_sessions} sessions'
    eyebrow = f'{dirname} · {d0} → {d1}'
    subtitle = (
        'Combined view of multiple Claude Code sessions. '
        'Each depth-1 block is one session; workers are its subagents.'
    )

    # --- auto day markers ---
    day_start = span_start.astimezone(dt.timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    day_end = span_end.astimezone(dt.timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    markers = []
    if day_start == day_end:
        # single day: one marker at the session start
        markers.append({
            'at': fmt_iso(span_start),
            'label': f'<b>{span_start.astimezone(dt.timezone.utc).strftime("%a %b %-d")}</b>',
        })
    else:
        cur = day_start
        while cur <= day_end:
            markers.append({
                'at': fmt_iso(cur),
                'label': f'<b>{cur.strftime("%a %b %-d")}</b>',
            })
            cur += dt.timedelta(days=1)

    graph = {
        'title': title,
        'eyebrow': eyebrow,
        'subtitle': subtitle,
        'orientation': 'horizontal',
        'agents': all_agents,
        'markers': markers,
        'extraStats': extra_stats,
    }

    # --- _meta.json overrides ---
    meta_path = os.path.join(dirpath, '_meta.json')
    if os.path.isfile(meta_path):
        try:
            meta = json.load(open(meta_path, encoding='utf-8'))
            for key in ('title', 'eyebrow', 'subtitle', 'extraStats', 'orientation', 'footer'):
                if key in meta:
                    graph[key] = meta[key]
        except (json.JSONDecodeError, OSError) as e:
            print(f'build_spa: warning: could not load _meta.json: {e}', file=sys.stderr)

    # CLI --orientation wins over everything
    if cli_orientation:
        graph['orientation'] = cli_orientation

    return graph


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def render_graph(graph, output_path):
    """Validate graph and write the SPA HTML to output_path."""
    validate(graph)

    orientation = graph.get('orientation') or 'vertical'
    if orientation not in ('vertical', 'horizontal'):
        die(f"graph.orientation must be 'vertical' or 'horizontal', got {orientation!r}")

    template = open(TEMPLATE, encoding='utf-8').read()
    title = graph.get('title') or (graph.get('session') or {}).get('id') or 'Agent graph'
    data_json = json.dumps(graph, ensure_ascii=False)
    data_json = data_json.replace('</', '<\\/')

    html = template.replace('__TITLE__', title.replace('<', '&lt;'))
    html = html.replace('__DATA_JSON__', data_json)
    html = html.replace('__ORIENTATION__', orientation)

    with open(output_path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(
        f'build_spa: wrote {output_path}  ({len(graph["agents"])} agents)',
        file=sys.stderr,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('graph', help='graph JSON file, or directory of per-session JSON files')
    ap.add_argument('-o', '--output', required=True, help='output HTML path')
    ap.add_argument(
        '--orientation', choices=['vertical', 'horizontal'], default=None,
        help="layout orientation (default: graph.orientation, else 'vertical'; "
             "'horizontal' default in dir mode)",
    )
    ap.add_argument(
        '--org', metavar='NAME', default='lexerdev',
        help='dir mode: keep only sessions whose repo belongs to this GitHub org '
             '(default: lexerdev); case-insensitive',
    )
    ap.add_argument(
        '--any-org', action='store_true',
        help='dir mode: disable org filtering and include sessions from any org',
    )
    args = ap.parse_args()

    if not os.path.isfile(TEMPLATE):
        die(f'template not found: {TEMPLATE}')

    if os.path.isdir(args.graph):
        graph = build_combined_graph(
            args.graph, args.orientation,
            org_target=args.org, any_org=args.any_org,
        )
    elif os.path.isfile(args.graph):
        try:
            graph = json.load(open(args.graph, encoding='utf-8'))
        except json.JSONDecodeError as e:
            die(f'invalid JSON: {e}')
        if args.orientation:
            graph['orientation'] = args.orientation
    else:
        die(f'graph not found: {args.graph}')

    render_graph(graph, args.output)


if __name__ == '__main__':
    main()
