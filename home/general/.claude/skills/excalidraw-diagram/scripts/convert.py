#!/usr/bin/env python3
"""Convert a mermaid `classDiagram` (direction LR) into an Excalidraw file.

Scope (v1): classDiagram + `direction LR` + composition edges (`*--`/`--*`)
+ optional member lists. No other mermaid diagram types are supported.

Usage: convert.py <input.mmd> <output.excalidraw>
"""
import json
import re
import sys
import uuid

FONT_SIZE = 22
FONT_FAMILY = 8  # matches the hand-converted reference boxes
CHAR_W = FONT_SIZE * 0.55
TITLE_OFFSET_Y = 20
DIVIDER_OFFSET_Y = 60.5
FIRST_MEMBER_OFFSET_Y = 77.0
MEMBER_LINE_H = 61.5
BASE_HEIGHT = 120.0
HEIGHT_A = 58.5
MIN_WIDTH = 150.0
PAD_X = 50.0
COL_GAP = 120.0
ROW_GAP = 40.0

PALETTE = [
    "#e7f5ff",  # blue
    "#e6fcf5",  # teal
    "#ebfbee",  # green
    "#f3f8e7",  # lime
    "#f5f1ff",  # purple
    "#fff0f4",  # pink
    "#fff5f5",  # red-tint
]


def new_id():
    return uuid.uuid4().hex[:20]


class Node:
    def __init__(self, node_id, label):
        self.id = node_id
        self.label = label
        self.members = []
        self.col = 0
        self.x = 0.0
        self.y = 0.0
        self.width = MIN_WIDTH
        self.height = BASE_HEIGHT
        # populated during render
        self.rect_id = None


CLASS_WITH_BODY_RE = re.compile(r'class\s+(\w+)\["([^"]+)"\]\s*\{')
CLASS_WITH_LABEL_RE = re.compile(r'class\s+(\w+)\["([^"]+)"\]\s*$')
CLASS_BARE_RE = re.compile(r'class\s+(\w+)\s*$')
EDGE_RE = re.compile(r'(\w+)\s*(\*--|--\*|--)\s*(\w+)')


def parse_mermaid(text):
    lines = [l.strip() for l in text.splitlines()]
    nodes = {}
    edges = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line or line.startswith("classDiagram") or line.startswith("direction"):
            i += 1
            continue
        m = CLASS_WITH_BODY_RE.match(line)
        if m:
            node_id, label = m.group(1), m.group(2)
            node = Node(node_id, label)
            i += 1
            while i < len(lines) and lines[i] != "}":
                member = lines[i].strip()
                if member:
                    node.members.append(member)
                i += 1
            nodes[node_id] = node
            i += 1
            continue
        m = CLASS_WITH_LABEL_RE.match(line)
        if m:
            node_id, label = m.group(1), m.group(2)
            nodes[node_id] = Node(node_id, label)
            i += 1
            continue
        m = CLASS_BARE_RE.match(line)
        if m:
            node_id = m.group(1)
            if node_id not in nodes:
                nodes[node_id] = Node(node_id, node_id)
            i += 1
            continue
        m = EDGE_RE.match(line)
        if m:
            a, op, b = m.group(1), m.group(2), m.group(3)
            if op == "*--":
                owner, other = a, b  # diamond at a (owner)
            elif op == "--*":
                owner, other = b, a  # diamond at b (owner)
            else:
                owner, other = None, None
            edges.append((a, b, owner, other))
            i += 1
            continue
        i += 1
    return nodes, edges


def compute_columns(nodes, edges):
    incoming = {nid: set() for nid in nodes}
    outgoing = {nid: [] for nid in nodes}
    for a, b, _, _ in edges:
        outgoing[a].append(b)
        incoming[b].add(a)
    col = {nid: 0 for nid in nodes}
    roots = [nid for nid in nodes if not incoming[nid]]
    if not roots:
        roots = list(nodes)

    def visit(nid, depth, seen):
        if depth > col[nid]:
            col[nid] = depth
        if nid in seen:
            return
        seen = seen | {nid}
        for child in outgoing[nid]:
            visit(child, col[nid] + 1, seen)

    for r in roots:
        visit(r, 0, set())
    for nid in nodes:
        nodes[nid].col = col[nid]
    return outgoing


def size_node(node):
    lines = [node.label] + [m for m in node.members]
    max_chars = max(len(l) for l in lines)
    node.width = max(MIN_WIDTH, max_chars * CHAR_W + PAD_X)
    n_members = len(node.members)
    node.height = BASE_HEIGHT if n_members <= 1 else HEIGHT_A + MEMBER_LINE_H * n_members


def layout(nodes, outgoing):
    for node in nodes.values():
        size_node(node)

    max_col = max((n.col for n in nodes.values()), default=0)
    columns = {c: [] for c in range(max_col + 1)}
    for node in nodes.values():
        columns[node.col].append(node)

    x = 0.0
    col_widths = {}
    for c in range(max_col + 1):
        col_nodes = columns[c]
        col_widths[c] = max((n.width for n in col_nodes), default=MIN_WIDTH)

    for c in range(max_col + 1):
        col_nodes = columns[c]
        total_h = sum(n.height for n in col_nodes) + ROW_GAP * max(0, len(col_nodes) - 1)
        y = -total_h / 2.0
        for n in col_nodes:
            n.x = x
            n.y = y
            y += n.height + ROW_GAP
        x += col_widths[c] + COL_GAP


def make_frame_less_box(node, color):
    """Return (rectangle, title_text, [line, member_text]) excalidraw elements for a node."""
    group_id = new_id() if node.members else None
    group_ids = [group_id] if group_id else []

    rect_id = new_id()
    node.rect_id = rect_id
    rect = {
        "id": rect_id, "type": "rectangle",
        "x": node.x, "y": node.y, "width": node.width, "height": node.height,
        "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": color,
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "groupIds": group_ids, "frameId": None,
        "roundness": None, "seed": 1, "version": 1, "versionNonce": 1,
        "isDeleted": False, "boundElements": [], "updated": 1, "link": None,
        "locked": False,
    }

    title = {
        "id": new_id(), "type": "text",
        "x": node.x + 21.3, "y": node.y + TITLE_OFFSET_Y,
        "width": len(node.label) * CHAR_W, "height": 27.5,
        "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": color,
        "fillStyle": "hachure", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "groupIds": group_ids, "frameId": None,
        "roundness": None, "seed": 1, "version": 1, "versionNonce": 1,
        "isDeleted": False, "boundElements": [], "updated": 1, "link": None,
        "locked": False,
        "text": node.label, "fontSize": FONT_SIZE, "fontFamily": FONT_FAMILY,
        "textAlign": "left", "verticalAlign": "top", "containerId": None,
        "originalText": node.label, "autoResize": True, "lineHeight": 1.25,
    }

    extras = []
    if node.members:
        line = {
            "id": new_id(), "type": "line",
            "x": node.x, "y": node.y + DIVIDER_OFFSET_Y,
            "width": node.width, "height": 1.0,
            "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": color,
            "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
            "roughness": 0, "opacity": 100, "groupIds": group_ids, "frameId": None,
            "roundness": None, "seed": 1, "version": 1, "versionNonce": 1,
            "isDeleted": False, "boundElements": None, "updated": 1, "link": None,
            "locked": False,
            "points": [[0, 0], [node.width, 0]],
            "startBinding": None, "endBinding": None,
            "startArrowhead": None, "endArrowhead": None, "polygon": False,
        }
        extras.append(line)
        for idx, member in enumerate(node.members):
            text = {
                "id": new_id(), "type": "text",
                "x": node.x + 21.3, "y": node.y + FIRST_MEMBER_OFFSET_Y + idx * MEMBER_LINE_H,
                "width": len(member) * CHAR_W, "height": 27.5,
                "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": color,
                "fillStyle": "hachure", "strokeWidth": 1, "strokeStyle": "solid",
                "roughness": 0, "opacity": 100, "groupIds": group_ids, "frameId": None,
                "roundness": None, "seed": 1, "version": 1, "versionNonce": 1,
                "isDeleted": False, "boundElements": [], "updated": 1, "link": None,
                "locked": False,
                "text": member, "fontSize": FONT_SIZE, "fontFamily": FONT_FAMILY,
                "textAlign": "left", "verticalAlign": "top", "containerId": None,
                "originalText": member, "autoResize": True, "lineHeight": 1.25,
            }
            extras.append(text)

    return rect, title, extras


def make_arrow(owner_node, other_node):
    """Elbowed composition arrow, diamond at owner_node's edge."""
    # owner -> other, left to right (owner is upstream column)
    start_x = owner_node.x + owner_node.width
    start_y = owner_node.y + owner_node.height / 2.0
    end_x = other_node.x
    end_y = other_node.y + other_node.height / 2.0

    mid_x = (start_x + end_x) / 2.0
    dx_end = end_x - start_x
    points = [
        [0, 0],
        [mid_x - start_x, 0],
        [mid_x - start_x, end_y - start_y],
        [dx_end, end_y - start_y],
    ]

    arrow_id = new_id()
    arrow = {
        "id": arrow_id, "type": "arrow",
        "x": start_x, "y": start_y,
        "width": abs(dx_end), "height": abs(end_y - start_y),
        "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": None, "seed": 1, "version": 1, "versionNonce": 1,
        "isDeleted": False, "boundElements": [], "updated": 1, "link": None,
        "locked": False,
        "points": points, "lastCommittedPoint": None,
        "startBinding": {
            "elementId": owner_node.rect_id, "mode": "orbit",
            "fixedPoint": [1.0, 0.5],
        },
        "endBinding": {
            "elementId": other_node.rect_id, "mode": "orbit",
            "fixedPoint": [0.0, 0.5],
        },
        "startArrowhead": "diamond", "endArrowhead": None,
        "elbowed": True, "fixedSegments": None,
        "startIsSpecial": None, "endIsSpecial": None,
    }
    return arrow


def convert(mermaid_text):
    nodes, edges = parse_mermaid(mermaid_text)
    outgoing = compute_columns(nodes, edges)
    layout(nodes, outgoing)

    elements = []
    for idx, node in enumerate(nodes.values()):
        color = PALETTE[idx % len(PALETTE)]
        rect, title, extras = make_frame_less_box(node, color)
        elements.append(rect)
        elements.append(title)
        elements.extend(extras)

    for a, b, owner, other in edges:
        if owner is None:
            owner, other = a, b
        arrow = make_arrow(nodes[owner], nodes[other])
        elements.append(arrow)
        nodes[owner].__dict__.setdefault("_bound", []).append(arrow["id"])
        nodes[other].__dict__.setdefault("_bound", []).append(arrow["id"])

    by_id = {e["id"]: e for e in elements}
    for node in nodes.values():
        bound = getattr(node, "_bound", [])
        if bound:
            by_id[node.rect_id]["boundElements"] = [
                {"id": aid, "type": "arrow"} for aid in bound
            ]

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://app.excalidraw.com",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


def main():
    if len(sys.argv) != 3:
        print("usage: convert.py <input.mmd> <output.excalidraw>", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1]) as f:
        text = f.read()
    doc = convert(text)
    with open(sys.argv[2], "w") as f:
        json.dump(doc, f, indent=2)


if __name__ == "__main__":
    main()
