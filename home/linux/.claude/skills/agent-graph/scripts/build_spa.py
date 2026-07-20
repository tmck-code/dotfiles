#!/usr/bin/env python3
"""Render a graph JSON into a standalone agent-graph SPA.

Reads a graph document (see REFERENCE.md) and the sibling `template.html`,
substitutes the data + title, and writes a single self-contained HTML file.
"""

import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, 'template.html')


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


def session_filenames(dirpath, tolerant):
    """List .ndjson filenames, preferring index.json ordering when tolerant."""
    names = sorted(f for f in os.listdir(dirpath) if f.endswith('.ndjson'))
    index_path = os.path.join(dirpath, 'index.json')
    if not (tolerant and os.path.isfile(index_path)):
        return names
    try:
        index = json.load(open(index_path, encoding='utf-8'))
        indexed = [f'{s["id"]}.ndjson' for s in index.get('sessions', []) if s.get('id')]
        if indexed:
            return indexed
    except (OSError, json.JSONDecodeError, TypeError, AttributeError) as e:
        print(f'build_spa: warning: unreadable index.json, using sorted listing: {e}', file=sys.stderr)
    return names


def load_sessions_dir(dirpath, tolerant=False):
    """Load all .ndjson session files from a directory.

    When tolerant, missing/broken files are skipped with a warning
    (mirroring the template's dynamic loader) instead of being fatal.
    """
    if not os.path.isdir(dirpath):
        die(f'sessions directory not found: {dirpath}')

    ndjson_files = session_filenames(dirpath, tolerant)
    if not ndjson_files:
        die(f'no .ndjson files found in {dirpath}')

    sessions = []
    for fname in ndjson_files:
        fpath = os.path.join(dirpath, fname)
        try:
            with open(fpath, encoding='utf-8') as fh:
                line = fh.readline().strip()
            if line:
                sessions.append(json.loads(line))
        except (OSError, json.JSONDecodeError) as e:
            if not tolerant:
                die(f'failed to load {fname}: {e}')
            print(f'build_spa: warning: skipping {fname}: {e}', file=sys.stderr)

    if not sessions:
        die(f'no loadable sessions in {dirpath}')
    return sessions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input', help='graph JSON path or sessions directory')
    ap.add_argument('-o', '--output', default=None, help='output HTML path (default: ./agent-graph.html in current dir)')
    ap.add_argument(
        '--orientation', choices=['vertical', 'horizontal'], default=None,
        help="layout orientation (default: graph.orientation, else 'vertical')",
    )
    ap.add_argument(
        '--embed', action='store_true',
        help='directory input: embed all sessions into a single self-contained HTML (no server needed)',
    )
    args = ap.parse_args()

    # Default output to current directory
    if not args.output:
        args.output = os.path.join(os.getcwd(), 'agent-graph.html')

    if not os.path.isfile(TEMPLATE):
        die(f'template not found: {TEMPLATE}')

    # Detect if input is a file or directory
    is_dir = os.path.isdir(args.input)
    is_file = os.path.isfile(args.input)

    if not is_dir and not is_file:
        die(f'input not found (not a file or directory): {args.input}')

    if is_dir:
        # Multi-session mode: load from directory
        sessions = load_sessions_dir(args.input, tolerant=args.embed)
        graph = {
            'draft': False,
            'multiSession': len(sessions) > 1 if args.embed else True,
            'sessions': sessions,
            'title': f'Agent graph ({len(sessions)} sessions)',
            'eyebrow': 'multi-session view',
            'subtitle': '',
            'footer': '',
            'agents': [],
            'markers': [],
        }
        # Merge all agents and markers from all sessions
        for sess in sessions:
            graph['agents'].extend(sess.get('agents', []))
            graph['markers'].extend(sess.get('markers', []))

        if args.embed:
            # Embed mode: everything goes into the static HTML, no sessions copy
            sessions_dir = None
        else:
            # Copy sessions directory to current working directory for easy access
            sessions_dir = os.path.abspath(args.input)
            cwd_sessions = os.path.join(os.getcwd(), 'sessions')
            if sessions_dir != cwd_sessions:
                if os.path.exists(cwd_sessions):
                    shutil.rmtree(cwd_sessions)
                shutil.copytree(sessions_dir, cwd_sessions)
                sessions_dir = cwd_sessions
                print(f'build_spa: copied sessions to {cwd_sessions}', file=sys.stderr)
    else:
        # Single-session mode: load from file
        if args.embed:
            print('build_spa: note: --embed has no effect for file input (already embedded)', file=sys.stderr)
        try:
            graph = json.load(open(args.input, encoding='utf-8'))
        except json.JSONDecodeError as e:
            die(f'invalid JSON: {e}')
        validate(graph)
        sessions_dir = None

    orientation = args.orientation or graph.get('orientation') or 'vertical'
    if orientation not in ('vertical', 'horizontal'):
        die(f"graph.orientation must be 'vertical' or 'horizontal', got {orientation!r}")

    template = open(TEMPLATE, encoding='utf-8').read()
    title = graph.get('title') or (graph.get('session') or {}).get('id') or 'Agent graph'

    if sessions_dir:
        # Dynamic mode: embed sessions dir path and empty data, template will fetch
        data_json = json.dumps({'sessions': []}, ensure_ascii=False)
        # Convert to relative path: use just the directory name if it's a sibling of output
        output_dir = os.path.dirname(os.path.abspath(args.output))
        sessions_abs = os.path.abspath(sessions_dir)
        try:
            sessions_rel = os.path.relpath(sessions_abs, output_dir)
        except ValueError:
            # On Windows, relpath can fail if on different drives; use absolute
            sessions_rel = sessions_abs
        html = template.replace('__TITLE__', title.replace('<', '&lt;'))
        html = html.replace('__DATA_JSON__', data_json)
        html = html.replace('__ORIENTATION__', orientation)
        html = html.replace('__SESSIONS_DIR__', sessions_rel)
        html = html.replace('__DYNAMIC_MODE__', 'true')
    else:
        # Static mode: embed all data
        data_json = json.dumps(graph, ensure_ascii=False)
        # guard against premature </script> termination inside the JSON blob
        data_json = data_json.replace('</', '<\\/')

        html = template.replace('__TITLE__', title.replace('<', '&lt;'))
        html = html.replace('__DATA_JSON__', data_json)
        html = html.replace('__ORIENTATION__', orientation)
        html = html.replace('__SESSIONS_DIR__', '')
        html = html.replace('__DYNAMIC_MODE__', 'false')

    # Wrap in proper HTML structure with charset declaration
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {html}
</head>
<body>
</body>
</html>"""

    with open(args.output, 'w', encoding='utf-8') as fh:
        fh.write(full_html)
    agent_count = len(graph.get('agents', []))
    print(f'build_spa: wrote {args.output}  ({agent_count} agents)', file=sys.stderr)


if __name__ == '__main__':
    main()
