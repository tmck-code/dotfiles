#!/usr/bin/env python3
"""Convert a mermaid `classDiagram` or `erDiagram` into an Excalidraw file.

Three input paths:

- `classDiagram` (direction LR) + composition edges (`*--`/`--*`) + optional
  member lists -> pastel UML boxes (the original v1 behaviour).
- `erDiagram` + entity attribute blocks + crowfoot relationships -> ERD
  tables styled after a hand-drawn ERD reference (colored header band,
  matching light body tint, mono rows, grey row dividers, PK/UK/FK colored
  rows).
- `flowchart` / `graph` + subgraphs + `classDef`/`class`/`style`/`linkStyle`
  -> rounded boxes styled after a hand-drawn decision-tree reference. See
  `flowchart.py`.
- `gantt` + sections + `name : start, end` tasks -> banded timeline with
  rounded bars and a unit grid, styled after a hand-converted reference. See
  `gantt.py`.
- `pie` (optionally `showData`) + `"label" : value` slices -> a hand-drawn
  pie chart with solid-filled wedges, percentage labels and a swatch legend,
  styled after a hand-drawn reference pie. See `pie.py`.

The diagram type is taken from the first directive line in the input.

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

# --- ERD table styling -------------------------------------------------
# Geometry reverse-engineered from the tables in a hand-drawn ERD
# reference diagram. Those were drawn at a huge zoom;
# every ratio below is that file's geometry divided through by its row
# font size, then re-multiplied by ERD_ROW_FONT.
ERD_ROW_FONT = 20.0
ERD_FONT_FAMILY = 3  # code / monospace
ERD_TITLE_FONT = ERD_ROW_FONT * 1.385
ERD_ROW_H = ERD_ROW_FONT * 2.307
ERD_HEADER_H = ERD_ROW_FONT * 3.075
ERD_TITLE_OFFSET_Y = ERD_ROW_FONT * 0.847
ERD_PAD_X = ERD_ROW_FONT * 0.77
ERD_CHAR_W = ERD_ROW_FONT * 0.6  # excalidraw's mono face
ERD_MIN_WIDTH = 260.0
ERD_COL_GAP = 160.0
ERD_ROW_GAP = 60.0
ERD_DIVIDER_COLOR = "#ced4da"
ERD_BORDER_COLOR = "#1e1e1e"
ERD_TITLE_COLOR = "#ffffff"
ERD_TEXT_COLOR = "#1e1e1e"
ERD_KEY_COLORS = {"PK": "#e67700", "UK": "#2f9e44", "FK": "#c92a2a"}
# (header band / body tint) pairs, cycled per entity — "style B" from the
# reference diagram, i.e. a tinted body rather than a transparent one.
ERD_PALETTE = [
    ("#1971c2", "#e7f5ff"),  # blue
    ("#2f9e44", "#ebfbee"),  # green
    ("#9c36b5", "#f8f0fc"),  # purple
    ("#e8590c", "#fff4e6"),  # orange
    ("#0c8599", "#e3fafc"),  # cyan
    ("#c2255c", "#fff0f6"),  # pink
]
# mermaid crowfoot cardinality -> excalidraw arrowhead
ERD_ARROWHEADS = {
    "||": "crowfoot_one",
    "|o": "circle_outline",
    "o|": "circle_outline",
    "}o": "crowfoot_many",
    "o{": "crowfoot_many",
    "}|": "crowfoot_one_or_many",
    "|{": "crowfoot_one_or_many",
}


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


# --- erDiagram ---------------------------------------------------------

ER_ENTITY_OPEN_RE = re.compile(r'^(\w+)\s*(?:\["([^"]+)"\])?\s*\{$')
ER_ENTITY_BARE_RE = re.compile(r'^(\w+)\s*(?:\["([^"]+)"\])?$')
ER_ATTR_RE = re.compile(
    r'^(?P<type>\S+)\s+(?P<name>\w+)'
    r'(?:\s+(?P<keys>(?:PK|FK|UK)(?:\s*,\s*(?:PK|FK|UK))*))?'
    r'(?:\s+"(?P<comment>[^"]*)")?$'
)
ER_REL_RE = re.compile(
    r'^(\w+)\s+(\|\||\|o|\}o|\}\|)(--|\.\.)(\|\||o\||o\{|\|\{)\s+(\w+)'
    r'\s*(?::\s*(?:"([^"]*)"|(\S.*?))\s*)?$'
)


class Entity(Node):
    def __init__(self, entity_id, label):
        super().__init__(entity_id, label)
        self.attrs = []  # list of (name, type, keys)
        self.rows = []   # rendered row strings, filled by size_entity


def parse_er(text):
    """Parse an `erDiagram` into (entities, relationships).

    Relationships are (left_id, right_id, left_card, right_card, dotted, label).
    """
    lines = [l.strip() for l in text.splitlines()]
    entities = {}
    rels = []

    def ensure(eid, label=None):
        if eid not in entities:
            entities[eid] = Entity(eid, label or eid)
        elif label:
            entities[eid].label = label
        return entities[eid]

    i = 0
    while i < len(lines):
        line = lines[i]
        if not line or line.startswith("erDiagram") or line.startswith("direction") \
                or line.startswith("%%"):
            i += 1
            continue

        m = ER_REL_RE.match(line)
        if m:
            left, lcard, link, rcard, right, qlabel, plabel = m.groups()
            ensure(left)
            ensure(right)
            rels.append((left, right, lcard, rcard, link == "..",
                         qlabel if qlabel is not None else (plabel or "")))
            i += 1
            continue

        m = ER_ENTITY_OPEN_RE.match(line)
        if m:
            entity = ensure(m.group(1), m.group(2))
            i += 1
            while i < len(lines) and lines[i] != "}":
                attr = lines[i].strip()
                am = ER_ATTR_RE.match(attr) if attr else None
                if am:
                    keys = am.group("keys") or ""
                    keys = ",".join(k.strip() for k in keys.split(",") if k.strip())
                    entity.attrs.append((am.group("name"), am.group("type"), keys))
                i += 1
            i += 1
            continue

        m = ER_ENTITY_BARE_RE.match(line)
        if m:
            ensure(m.group(1), m.group(2))
            i += 1
            continue

        i += 1
    return entities, rels


def size_entity(entity):
    """Lay out the attribute columns and set the entity's box size."""
    if entity.attrs:
        name_w = max(len(a[0]) for a in entity.attrs) + 2
        type_w = max(len(a[1]) for a in entity.attrs) + 3
    else:
        name_w = type_w = 0
    entity.rows = [
        (f"{name:<{name_w}}{type_:<{type_w}}{keys}".rstrip(), keys)
        for name, type_, keys in entity.attrs
    ]
    widest = max([len(r[0]) for r in entity.rows] or [0])
    title_w = len(entity.label) * ERD_TITLE_FONT * 0.6
    entity.width = max(
        ERD_MIN_WIDTH,
        widest * ERD_CHAR_W + 2 * ERD_PAD_X,
        title_w + 2 * ERD_PAD_X,
    )
    entity.height = ERD_HEADER_H + ERD_ROW_H * len(entity.rows)


def er_layout(entities):
    for entity in entities.values():
        size_entity(entity)
    max_col = max((e.col for e in entities.values()), default=0)
    columns = {c: [] for c in range(max_col + 1)}
    for entity in entities.values():
        columns[entity.col].append(entity)
    x = 0.0
    for c in range(max_col + 1):
        col_entities = columns[c]
        total_h = (sum(e.height for e in col_entities)
                   + ERD_ROW_GAP * max(0, len(col_entities) - 1))
        y = -total_h / 2.0
        for e in col_entities:
            e.x = x
            e.y = y
            y += e.height + ERD_ROW_GAP
        x += max((e.width for e in col_entities), default=ERD_MIN_WIDTH) + ERD_COL_GAP


def _base(el_id, el_type, x, y, width, height, group_ids, **extra):
    el = {
        "id": el_id, "type": el_type,
        "x": x, "y": y, "width": width, "height": height,
        "angle": 0, "strokeColor": ERD_BORDER_COLOR,
        "backgroundColor": "transparent", "fillStyle": "solid",
        "strokeWidth": 1, "strokeStyle": "solid", "roughness": 0,
        "opacity": 100, "groupIds": group_ids, "frameId": None,
        "roundness": None, "seed": 1, "version": 1, "versionNonce": 1,
        "isDeleted": False, "boundElements": [], "updated": 1, "link": None,
        "locked": False,
    }
    el.update(extra)
    return el


def _erd_text(text, x, y, width, color, font_size, align, group_ids):
    return _base(
        new_id(), "text", x, y, width, font_size * 1.25, group_ids,
        strokeColor=color, text=text, originalText=text,
        fontSize=font_size, fontFamily=ERD_FONT_FAMILY,
        textAlign=align, verticalAlign="top", containerId=None,
        autoResize=False, lineHeight=1.25,
    )


def make_erd_table(entity, accent, tint):
    """Return the excalidraw elements for one ERD table (style B: tinted body)."""
    group_ids = [new_id()]
    els = []

    # body tint, then the header band, then the outer border on top
    els.append(_base(new_id(), "rectangle", entity.x, entity.y,
                     entity.width, entity.height, group_ids,
                     strokeColor=accent, backgroundColor=tint))
    els.append(_base(new_id(), "rectangle", entity.x, entity.y,
                     entity.width, ERD_HEADER_H, group_ids,
                     strokeColor=accent, backgroundColor=accent))
    rect_id = new_id()
    entity.rect_id = rect_id
    els.append(_base(rect_id, "rectangle", entity.x, entity.y,
                     entity.width, entity.height, group_ids,
                     strokeColor=ERD_BORDER_COLOR, strokeWidth=2))

    els.append(_erd_text(entity.label, entity.x,
                         entity.y + ERD_TITLE_OFFSET_Y, entity.width,
                         ERD_TITLE_COLOR, ERD_TITLE_FONT, "center", group_ids))

    text_w = entity.width - 2 * ERD_PAD_X
    row_text_dy = (ERD_ROW_H - ERD_ROW_FONT * 1.25) / 2.0
    for idx, (row, keys) in enumerate(entity.rows):
        top = entity.y + ERD_HEADER_H + idx * ERD_ROW_H
        els.append(_base(new_id(), "line", entity.x, top, entity.width, 0.0,
                         group_ids, strokeColor=ERD_DIVIDER_COLOR,
                         points=[[0, 0], [entity.width, 0]],
                         startBinding=None, endBinding=None,
                         startArrowhead=None, endArrowhead=None,
                         lastCommittedPoint=None, polygon=False,
                         boundElements=None))
        color = ERD_TEXT_COLOR
        for key in keys.split(","):
            if key in ERD_KEY_COLORS:
                color = ERD_KEY_COLORS[key]
                break
        els.append(_erd_text(row, entity.x + ERD_PAD_X, top + row_text_dy,
                             text_w, color, ERD_ROW_FONT, "left", group_ids))
    return els


def make_er_arrow(left, right, lcard, rcard, dotted, label):
    """Elbowed relationship arrow with crowfoot arrowheads at both ends."""
    start_x = left.x + left.width
    start_y = left.y + left.height / 2.0
    end_x = right.x
    end_y = right.y + right.height / 2.0
    mid_x = (start_x + end_x) / 2.0
    dx_end = end_x - start_x
    points = [
        [0, 0],
        [mid_x - start_x, 0],
        [mid_x - start_x, end_y - start_y],
        [dx_end, end_y - start_y],
    ]
    arrow = _base(
        new_id(), "arrow", start_x, start_y, abs(dx_end), abs(end_y - start_y),
        [], strokeWidth=2, strokeStyle="dashed" if dotted else "solid",
        points=points, lastCommittedPoint=None,
        startBinding={"elementId": left.rect_id, "mode": "orbit",
                      "fixedPoint": [1.0, 0.5]},
        endBinding={"elementId": right.rect_id, "mode": "orbit",
                    "fixedPoint": [0.0, 0.5]},
        startArrowhead=ERD_ARROWHEADS.get(lcard),
        endArrowhead=ERD_ARROWHEADS.get(rcard),
        elbowed=True, fixedSegments=None,
        startIsSpecial=None, endIsSpecial=None,
    )
    els = [arrow]
    if label:
        text = _erd_text(label, mid_x, (start_y + end_y) / 2.0,
                         len(label) * ERD_CHAR_W, ERD_TEXT_COLOR,
                         ERD_ROW_FONT * 0.7, "center", [])
        text["containerId"] = arrow["id"]
        text["verticalAlign"] = "middle"
        arrow["boundElements"] = [{"id": text["id"], "type": "text"}]
        els.append(text)
    return els


def convert_er(mermaid_text):
    entities, rels = parse_er(mermaid_text)
    compute_columns(entities, [(l, r, None, None) for l, r, *_ in rels])
    er_layout(entities)

    elements = []
    for idx, entity in enumerate(entities.values()):
        accent, tint = ERD_PALETTE[idx % len(ERD_PALETTE)]
        elements.extend(make_erd_table(entity, accent, tint))

    bound = {eid: [] for eid in entities}
    for left, right, lcard, rcard, dotted, label in rels:
        a, b = entities[left], entities[right]
        if a.col > b.col:  # always draw left-to-right
            a, b = b, a
            lcard, rcard = rcard, lcard
        arrow_els = make_er_arrow(a, b, lcard, rcard, dotted, label)
        elements.extend(arrow_els)
        bound[a.id].append(arrow_els[0]["id"])
        bound[b.id].append(arrow_els[0]["id"])

    by_id = {e["id"]: e for e in elements}
    for entity in entities.values():
        if bound[entity.id]:
            by_id[entity.rect_id]["boundElements"] = [
                {"id": aid, "type": "arrow"} for aid in bound[entity.id]
            ]
    return elements


def convert(mermaid_text):
    if re.search(r'^\s*(?:flowchart|graph)\s', mermaid_text, re.M):
        from flowchart import convert_flowchart
        return document(convert_flowchart(mermaid_text))
    if re.search(r'^\s*gantt\b', mermaid_text, re.M):
        from gantt import convert_gantt
        return document(convert_gantt(mermaid_text))
    if re.search(r'^\s*pie\b', mermaid_text, re.M):
        from pie import convert_pie
        return document(convert_pie(mermaid_text))
    if re.search(r'^\s*erDiagram\b', mermaid_text, re.M):
        elements = convert_er(mermaid_text)
        return document(elements)
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

    return document(elements)


def document(elements):
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
