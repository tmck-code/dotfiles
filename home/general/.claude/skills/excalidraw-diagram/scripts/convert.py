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
- `gantt` + sections + `name : [tags,] [id,] [start,] end` tasks -> banded
  timeline with rounded bars and a unit grid, styled after a hand-converted
  reference. Numeric axis, or a date axis via `dateFormat YYYY-MM-DD` with
  `Nd`/`Nh`/`Nw` durations, `after`/`until` references, `excludes weekends`
  (axis compressed to working days), `done`/`active`/`crit` bar styling and
  `milestone` diamonds. See `gantt.py`.
- `pie` (optionally `showData`) + `"label" : value` slices -> a hand-drawn
  pie chart with solid-filled wedges, percentage labels and a swatch legend,
  styled after a hand-drawn reference pie. See `pie.py`.
- `sequenceDiagram` + `participant`/`actor` declarations, messages, notes and
  `par`/`loop`/`alt`/`opt`/`rect` blocks -> participant headers over grey
  lifelines with bound message labels, styled after a reference conversion of
  this skill's own example. See `sequence.py`.
- `quadrantChart` + `title`, `x-axis`/`y-axis` labels, `quadrant-1..4`
  labels and `name: [x, y]` points -> a 2x2 grid of tinted squares with
  rotated y-axis labels, solid dots with labels that flip to stay inside the
  chart and clear of each other, styled after a hand-drawn reference. See
  `quadrant.py`.
- `xychart-beta` (optionally `horizontal`) + `title`, a categorical
  `x-axis`, a `y-axis` label/range and `bar`/`line` series -> a bar chart
  with grouped bars, optional line overlays, gridlines, tilted category
  labels and a legend. See `bar.py`.

The diagram type is taken from the first directive line in the input.

Usage: convert.py <input.mmd> <output.excalidraw> [--sloppiness 1|2|3]

`--scale` multiplies all geometry and font sizes (default 1.5), matching the
size a converted diagram is normally resized to by hand. Stroke widths are
left alone, as Excalidraw does on a drag-resize.

`--corners sharp|round` sets the corner style of boxes. Omitted, each diagram
type keeps its own native style (ERD tables are sharp; flowchart boxes and
gantt bars are rounded). It never touches arrows or lines, where `roundness`
means curve smoothing rather than corners.

`--sloppiness` maps to Excalidraw's sloppiness control: 1 = architect (clean,
the default), 2 = artist, 3 = cartoonist. It applies to shapes only —
arrows and straight lines always stay at the cleanest setting so connectors
and dividers remain crisp.
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
ERD_RANK_GAP = 120.0  # gap between ranks in `direction TB` layouts
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

ER_ENTITY_OPEN_RE = re.compile(r'^([\w-]+)\s*(?:\["([^"]+)"\])?\s*\{$')
ER_ENTITY_BARE_RE = re.compile(r'^([\w-]+)\s*(?:\["([^"]+)"\])?$')
ER_ATTR_RE = re.compile(
    r'^(?P<type>\S+)\s+(?P<name>\w+)'
    r'(?:\s+(?P<keys>(?:PK|FK|UK)(?:\s*,\s*(?:PK|FK|UK))*))?'
    r'(?:\s+"(?P<comment>[^"]*)")?$'
)
ER_REL_RE = re.compile(
    r'^([\w-]+)\s+(\|\||\|o|\}o|\}\|)(--|\.\.)(\|\||o\||o\{|\|\{)\s+([\w-]+)'
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


def er_layout(entities, vertical=False):
    for entity in entities.values():
        size_entity(entity)
    max_col = max((e.col for e in entities.values()), default=0)
    columns = {c: [] for c in range(max_col + 1)}
    for entity in entities.values():
        columns[entity.col].append(entity)
    if vertical:
        # ranks stack top-to-bottom; entities within a rank sit side by side
        y = 0.0
        for c in range(max_col + 1):
            rank = columns[c]
            total_w = (sum(e.width for e in rank)
                       + ERD_COL_GAP * max(0, len(rank) - 1))
            x = -total_w / 2.0
            for e in rank:
                e.x = x
                e.y = y
                x += e.width + ERD_COL_GAP
            y += max((e.height for e in rank), default=0.0) + ERD_RANK_GAP
        return
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


def make_er_arrow(left, right, lcard, rcard, dotted, label, vertical=False):
    """Elbowed relationship arrow with crowfoot arrowheads at both ends."""
    if vertical:
        start_x = left.x + left.width / 2.0
        start_y = left.y + left.height
        end_x = right.x + right.width / 2.0
        end_y = right.y
        mid_y = (start_y + end_y) / 2.0
        dx_end = end_x - start_x
        points = [
            [0, 0],
            [0, mid_y - start_y],
            [dx_end, mid_y - start_y],
            [dx_end, end_y - start_y],
        ]
        start_fixed, end_fixed = [0.5, 1.0], [0.5, 0.0]
    else:
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
        start_fixed, end_fixed = [1.0, 0.5], [0.0, 0.5]
    arrow = _base(
        new_id(), "arrow", start_x, start_y, abs(dx_end), abs(end_y - start_y),
        [], strokeWidth=2, strokeStyle="dashed" if dotted else "solid",
        points=points, lastCommittedPoint=None,
        startBinding={"elementId": left.rect_id, "mode": "orbit",
                      "fixedPoint": start_fixed},
        endBinding={"elementId": right.rect_id, "mode": "orbit",
                    "fixedPoint": end_fixed},
        startArrowhead=ERD_ARROWHEADS.get(lcard),
        endArrowhead=ERD_ARROWHEADS.get(rcard),
        elbowed=True, fixedSegments=None,
        startIsSpecial=None, endIsSpecial=None,
    )
    els = [arrow]
    if label:
        text = _erd_text(label, (start_x + end_x) / 2.0,
                         (start_y + end_y) / 2.0,
                         len(label) * ERD_CHAR_W, ERD_TEXT_COLOR,
                         ERD_ROW_FONT * 0.7, "center", [])
        text["containerId"] = arrow["id"]
        text["verticalAlign"] = "middle"
        arrow["boundElements"] = [{"id": text["id"], "type": "text"}]
        els.append(text)
    return els


ER_DIRECTION_RE = re.compile(r'^\s*direction\s+(TB|TD|BT|LR|RL)\s*$', re.M)


def convert_er(mermaid_text):
    m = ER_DIRECTION_RE.search(mermaid_text)
    vertical = bool(m) and m.group(1) in ("TB", "TD", "BT")
    entities, rels = parse_er(mermaid_text)
    compute_columns(entities, [(l, r, None, None) for l, r, *_ in rels])
    er_layout(entities, vertical=vertical)

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
        arrow_els = make_er_arrow(a, b, lcard, rcard, dotted, label,
                                  vertical=vertical)
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


# Diagrams are emitted at a compact base size; everything is scaled up by this
# factor so a converted diagram lands on the canvas at a comfortable working
# size (measured from a hand-resized reference scene, which came out at
# ~1.48x). Stroke widths are deliberately not scaled — Excalidraw leaves them
# alone when you drag-resize a selection, and the thinner relative stroke is
# part of the look.
DEFAULT_SCALE = 1.5
SCALED_KEYS = ("x", "y", "width", "height", "fontSize")


def apply_scale(elements, scale):
    """Scale geometry and type size by `scale`, leaving stroke widths alone."""
    if scale == 1:
        return elements
    for el in elements:
        for key in SCALED_KEYS:
            if isinstance(el.get(key), (int, float)):
                el[key] = el[key] * scale
        points = el.get("points")
        if points:
            el["points"] = [[x * scale, y * scale] for x, y in points]
        roundness = el.get("roundness")
        if isinstance(roundness, dict) and "value" in roundness:
            roundness["value"] = roundness["value"] * scale
    return elements


def convert(mermaid_text, sloppiness=1, corners=None, scale=DEFAULT_SCALE):
    doc = _convert(mermaid_text)
    apply_sloppiness(doc["elements"], sloppiness)
    apply_corners(doc["elements"], corners)
    apply_scale(doc["elements"], scale)
    return doc


def _convert(mermaid_text):
    if re.search(r'^\s*(?:flowchart|graph)\s', mermaid_text, re.M):
        from flowchart import convert_flowchart
        return document(convert_flowchart(mermaid_text))
    if re.search(r'^\s*gantt\b', mermaid_text, re.M):
        from gantt import convert_gantt
        return document(convert_gantt(mermaid_text))
    if re.search(r'^\s*pie\b', mermaid_text, re.M):
        from pie import convert_pie
        return document(convert_pie(mermaid_text))
    if re.search(r'^\s*sequenceDiagram\b', mermaid_text, re.M):
        from sequence import convert_sequence
        return document(convert_sequence(mermaid_text))
    if re.search(r'^\s*xychart-beta\b', mermaid_text, re.M):
        from bar import convert_bar
        return document(convert_bar(mermaid_text))
    if re.search(r'^\s*quadrantChart\b', mermaid_text, re.M):
        from quadrant import convert_quadrant
        return document(convert_quadrant(mermaid_text))
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


def finalise(elements):
    """Fill the fields Excalidraw's current element schema (and the
    Excalidraw+ REST API validator) require but the emitters don't set:
    a fractional `index` per element, and `mode` + `fixedPoint` on every
    arrow binding. fixedPoint is the arrow endpoint normalised to the bound
    shape's box.
    """
    by_id = {e["id"]: e for e in elements}
    for i, el in enumerate(elements):
        el["index"] = "a" + format(i, "04d")
        if el.get("type") != "arrow":
            continue
        pts = el["points"]
        for key, pt in (("startBinding", pts[0]), ("endBinding", pts[-1])):
            binding = el.get(key)
            if not binding:
                continue
            shape = by_id[binding["elementId"]]
            ax, ay = el["x"] + pt[0], el["y"] + pt[1]
            fx = (ax - shape["x"]) / shape["width"] if shape["width"] else 0.5
            fy = (ay - shape["y"]) / shape["height"] if shape["height"] else 0.5
            # not clamped to [0,1]: a sequence message binds to its participant's
            # *header* box while sitting far below it, so fy is legitimately > 1
            # (the hand-converted reference does the same). Every other path
            # anchors on the shape's own edge, so this is a no-op there.
            binding["fixedPoint"] = [round(fx, 6), round(fy, 6)]
            binding["mode"] = "orbit"
    return elements


# Excalidraw sloppiness (1/2/3 in the UI) -> the element `roughness` field.
SLOPPINESS_ROUGHNESS = {1: 0, 2: 1, 3: 2}
SLOPPY_TYPES = {"rectangle", "ellipse", "diamond"}


def apply_sloppiness(elements, sloppiness):
    """Set `roughness` on shapes from a 1/2/3 sloppiness level.

    Arrows and straight (two-point) lines are left at roughness 0 so
    connectors, dividers and table rules stay crisp. Multi-point lines are
    closed/curved shapes (pie wedges, logo marks) and follow the shapes.
    """
    if sloppiness not in SLOPPINESS_ROUGHNESS:
        raise ValueError("sloppiness must be 1, 2 or 3")
    roughness = SLOPPINESS_ROUGHNESS[sloppiness]
    if not roughness:
        return elements
    for el in elements:
        el_type = el.get("type")
        if el_type in SLOPPY_TYPES or (
                el_type == "line" and len(el.get("points") or []) > 2):
            el["roughness"] = roughness
    return elements


# Corner style for boxes. `{"type": 3}` is Excalidraw's adaptive-radius
# rounding; None is a sharp corner. Only box-like shapes are affected —
# on arrows/lines `roundness` controls curve smoothing, not corners.
CORNER_ROUNDNESS = {"sharp": None, "round": {"type": 3}}
CORNER_TYPES = {"rectangle", "diamond"}


def apply_corners(elements, corners):
    """Force sharp or round corners on every box in the diagram.

    `corners` of None leaves each emitter's own choice untouched.
    """
    if corners is None:
        return elements
    if corners not in CORNER_ROUNDNESS:
        raise ValueError("corners must be 'sharp' or 'round'")
    roundness = CORNER_ROUNDNESS[corners]
    for el in elements:
        if el.get("type") in CORNER_TYPES:
            el["roundness"] = dict(roundness) if roundness else None
    return elements


def document(elements):
    finalise(elements)
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://app.excalidraw.com",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


USAGE = ("usage: convert.py <input.mmd> <output.excalidraw> "
         "[--sloppiness 1|2|3] [--corners sharp|round] [--scale N]")


def take_option(args, flag, allowed):
    """Pull `--flag value` out of `args`, or return None if absent."""
    if flag not in args:
        return None
    i = args.index(flag)
    if i + 1 >= len(args) or args[i + 1] not in allowed:
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    value = args[i + 1]
    del args[i:i + 2]
    return value


def main():
    args = sys.argv[1:]
    sloppiness = take_option(args, "--sloppiness", ("1", "2", "3"))
    sloppiness = int(sloppiness) if sloppiness else 1
    corners = take_option(args, "--corners", ("sharp", "round"))
    scale = DEFAULT_SCALE
    if "--scale" in args:
        i = args.index("--scale")
        try:
            scale = float(args[i + 1])
        except (IndexError, ValueError):
            print(USAGE, file=sys.stderr)
            sys.exit(1)
        del args[i:i + 2]
    if len(args) != 2:
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    with open(args[0]) as f:
        text = f.read()
    doc = convert(text, sloppiness=sloppiness, corners=corners, scale=scale)
    with open(args[1], "w") as f:
        json.dump(doc, f, indent=2)


if __name__ == "__main__":
    main()
