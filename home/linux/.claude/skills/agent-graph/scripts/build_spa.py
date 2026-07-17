#!/usr/bin/env python3
"""Render a graph JSON into a standalone agent-graph SPA.

Reads a graph document (see REFERENCE.md) and the sibling `template.html`,
substitutes the data + title, and writes a single self-contained HTML file.
"""

import argparse
import json
import os
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


def load_sessions_dir(dirpath):
    """Load all .ndjson session files from a directory."""
    if not os.path.isdir(dirpath):
        die(f'sessions directory not found: {dirpath}')

    ndjson_files = sorted([f for f in os.listdir(dirpath) if f.endswith('.ndjson')])
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
            die(f'failed to load {fname}: {e}')

    return sessions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input', help='graph JSON path or sessions directory')
    ap.add_argument('-o', '--output', required=True, help='output HTML path')
    ap.add_argument(
        '--orientation', choices=['vertical', 'horizontal'], default=None,
        help="layout orientation (default: graph.orientation, else 'vertical')",
    )
    args = ap.parse_args()

    if not os.path.isfile(TEMPLATE):
        die(f'template not found: {TEMPLATE}')

    # Detect if input is a file or directory
    is_dir = os.path.isdir(args.input)
    is_file = os.path.isfile(args.input)

    if not is_dir and not is_file:
        die(f'input not found (not a file or directory): {args.input}')

    if is_dir:
        # Multi-session mode: load from directory
        sessions = load_sessions_dir(args.input)
        graph = {
            'draft': False,
            'multiSession': True,
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
        sessions_dir = args.input
    else:
        # Single-session mode: load from file
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
