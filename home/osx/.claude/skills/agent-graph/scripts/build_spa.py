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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('graph', help='graph JSON path')
    ap.add_argument('-o', '--output', required=True, help='output HTML path')
    ap.add_argument(
        '--orientation', choices=['vertical', 'horizontal'], default=None,
        help="layout orientation (default: graph.orientation, else 'vertical')",
    )
    args = ap.parse_args()

    if not os.path.isfile(args.graph):
        die(f'graph not found: {args.graph}')
    if not os.path.isfile(TEMPLATE):
        die(f'template not found: {TEMPLATE}')

    try:
        graph = json.load(open(args.graph, encoding='utf-8'))
    except json.JSONDecodeError as e:
        die(f'invalid JSON: {e}')

    validate(graph)

    orientation = args.orientation or graph.get('orientation') or 'vertical'
    if orientation not in ('vertical', 'horizontal'):
        die(f"graph.orientation must be 'vertical' or 'horizontal', got {orientation!r}")

    template = open(TEMPLATE, encoding='utf-8').read()
    title = graph.get('title') or (graph.get('session') or {}).get('id') or 'Agent graph'
    data_json = json.dumps(graph, ensure_ascii=False)
    # guard against premature </script> termination inside the JSON blob
    data_json = data_json.replace('</', '<\\/')

    html = template.replace('__TITLE__', title.replace('<', '&lt;'))
    html = html.replace('__DATA_JSON__', data_json)
    html = html.replace('__ORIENTATION__', orientation)

    with open(args.output, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f'build_spa: wrote {args.output}  ({len(graph["agents"])} agents)', file=sys.stderr)


if __name__ == '__main__':
    main()
