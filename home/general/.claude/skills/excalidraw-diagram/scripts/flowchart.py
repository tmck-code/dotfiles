#!/usr/bin/env python3
"""mermaid `flowchart` / `graph` -> excalidraw elements.

Styled after the decision tree in a hand-drawn reference diagram:
rounded rectangles with an 8px corner radius, a hand-drawn font, a saturated stroke over a matching pale
fill, and the label in the stroke colour.

Imported by convert.py; not meant to be run directly.
"""
import re
import uuid

FONT_FAMILY = 8  # Comic Shanns, as in the hand-drawn reference
LABEL_FONT = 18.0
EDGE_LABEL_FONT = 13.0
LINE_H = 1.25
CHAR_W = 0.58  # fraction of font size, for the hand-drawn face

NODE_PAD_X = 24.0
NODE_PAD_Y = 18.0
MIN_NODE_W = 150.0
MIN_NODE_H = 62.0
DIAMOND_SCALE = 1.55  # a diamond needs more box to fit the same text

COL_GAP = 150.0
NODE_GAP = 46.0        # floor gap between stacked members (unlabelled edge)
CLUSTER_GAP = 60.0
CLUSTER_PAD = 28.0
CLUSTER_STROKE = "#868e96"
CLUSTER_TITLE_COLOR = "#495057"
CLUSTER_TITLE_FONT = 16.0
TITLE_TEXT_H = CLUSTER_TITLE_FONT * LINE_H   # 20, as in the reference
TITLE_GAP = 10.0       # air between a title's box and the container top edge

EDGE_LABEL_WRAP = 24   # chars; long edge labels are wrapped to this width
LABEL_PAD = 18.0       # air around an edge label inside the gap it must fit

ROUTE_MARGIN = 14.0    # obstacles are inflated by this before routing
ROUTE_RING = 40.0      # how far outside the diagram bbox the outer lanes run
TURN_PENALTY = 60.0    # cost of an elbow, so routes prefer few of them

EDGE_COLOR = "#1e1e1e"
EDGE_LABEL_COLOR = "#495057"
DEFAULT_STYLE = ("#495057", "#f8f9fa")

# (stroke, fill) pairs, cycled over nodes that no classDef claims
PALETTE = [
    ("#a855f7", "#f3e8ff"),
    ("#0ea5e9", "#e0f2fe"),
    ("#22c55e", "#dcfce7"),
    ("#f59e0b", "#fef3c7"),
    ("#6366f1", "#e0e7ff"),
    ("#ef4444", "#fee2e2"),
]

# mermaid shape delimiters -> (excalidraw type, rounded?)
SHAPES = [
    ("[(", ")]", "rectangle", True),    # cylinder / database
    ("((", "))", "ellipse", False),
    ("([", "])", "rectangle", True),    # stadium
    ("[[", "]]", "rectangle", False),   # subroutine
    ("{{", "}}", "diamond", False),     # hexagon
    ("[", "]", "rectangle", False),
    ("(", ")", "rectangle", True),
    ("{", "}", "diamond", False),
    (">", "]", "rectangle", True),      # asymmetric
]

DIRECTIVE_RE = re.compile(r'^\s*(?:flowchart|graph)\s+(\w+)?')
SUBGRAPH_RE = re.compile(r'^subgraph\s+(\w+)\s*(?:\[(.+)\]|\("(.+)"\))?\s*$')
CLASSDEF_RE = re.compile(r'^classDef\s+(\w+)\s+(.*)$')
CLASS_RE = re.compile(r'^class\s+([\w,\s]+?)\s+(\w+)\s*$')
STYLE_RE = re.compile(r'^style\s+(\w+)\s+(.*)$')
LINKSTYLE_RE = re.compile(r'^linkStyle\s+([\d,\s]+)\s+(.*)$')
NODE_TOKEN = r'\w+(?:\[\(.*?\)\]|\(\(.*?\)\)|\(\[.*?\]\)|\[\[.*?\]\]|\{\{.*?\}\}|\[.*?\]|\(.*?\)|\{.*?\}|>.*?\])?'
LINK = r'-\.->|-\.-|-->|---|==>|===|->'
EDGE_RE = re.compile(
    rf'^(?P<a>{NODE_TOKEN})\s*(?P<link>{LINK})\s*(?:\|\s*(?P<label>.*?)\s*\|\s*)?'
    rf'(?P<b>{NODE_TOKEN})\s*$'
)
# `A -- text --> B` and `A -. text .-> B`, normalised to the `|text|` form
MID_LABEL_RE = re.compile(r'(--|-\.)\s+(.+?)\s+(-->|---|\.->|\.-)')


def new_id():
    return uuid.uuid4().hex[:20]


def clean_label(raw):
    if raw is None:
        return ""
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in '"\'':
        text = text[1:-1]
    text = re.sub(r'<br\s*/?>', "\n", text)
    for entity, char in (("&quot;", '"'), ("#quot;", '"'), ("&amp;", "&"),
                         ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " ")):
        text = text.replace(entity, char)
    return text.strip()


def wrap_label(text, width=EDGE_LABEL_WRAP):
    """Greedy word-wrap to `width` chars, preserving explicit newlines.

    Edge labels are otherwise emitted as one long line, which both sticks out
    sideways over neighbouring boxes and forces an absurdly wide column
    gutter; the hand-drawn reference wraps them onto 2-3 lines instead.
    """
    out = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            candidate = f"{line} {word}".strip()
            if line and len(candidate) > width:
                out.append(line)
                line = word
            else:
                line = candidate
        out.append(line)
    return "\n".join(out)


def text_size(text, font):
    lines = text.split("\n") or [""]
    return (max(len(l) for l in lines) * font * CHAR_W,
            len(lines) * font * LINE_H)


def parse_shape(token):
    """Split `ID[(label)]` into (node_id, excalidraw type, rounded, label)."""
    m = re.match(r'^(\w+)(.*)$', token.strip())
    node_id, rest = m.group(1), m.group(2)
    for open_d, close_d, kind, rounded in SHAPES:
        if rest.startswith(open_d) and rest.endswith(close_d):
            return node_id, kind, rounded, clean_label(rest[len(open_d):-len(close_d)])
    return node_id, None, None, None


class FlowNode:
    def __init__(self, node_id):
        self.id = node_id
        self.label = node_id
        self.kind = "rectangle"
        self.rounded = True
        self.classes = []
        self.style = None       # explicit `style` line wins over classDef
        self.cluster = None
        self.x = self.y = 0.0
        self.width = MIN_NODE_W
        self.height = MIN_NODE_H
        self.shape_id = None
        self.resolved = DEFAULT_STYLE + (2,)
        self.slot = 0
        self.group = None

    @property
    def lines(self):
        return self.label.split("\n") or [""]


class Cluster:
    def __init__(self, cluster_id, title):
        self.id = cluster_id
        self.title = title
        self.members = []
        self.gaps = []          # gap after each member but the last
        self.col = 0
        self.x = self.y = 0.0
        self.width = self.height = 0.0


def parse_style(decl):
    """`fill:#eee,stroke:#333,stroke-width:2px` -> dict."""
    out = {}
    for part in decl.replace(";", ",").split(","):
        if ":" not in part:
            continue
        key, _, value = part.partition(":")
        out[key.strip()] = value.strip()
    return out


def parse_flowchart(text):
    """Return (nodes, edges, clusters, classdefs, linkstyles)."""
    nodes = {}
    edges = []          # dicts: a, b, label, dotted, arrowhead
    clusters = []
    classdefs = {}
    linkstyles = {}
    stack = []          # open subgraph ids

    def ensure(token):
        node_id, kind, rounded, label = parse_shape(token)
        node = nodes.get(node_id)
        if node is None:
            node = nodes[node_id] = FlowNode(node_id)
            if stack:
                node.cluster = stack[-1]
                _cluster_by_id(clusters, stack[-1]).members.append(node_id)
        if kind:  # a shape was given here, so this is the definition site
            node.kind, node.rounded, node.label = kind, rounded, label or node_id
        return node

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("%%") or DIRECTIVE_RE.match(line):
            continue
        if line == "end":
            if stack:
                stack.pop()
            continue

        m = SUBGRAPH_RE.match(line)
        if m:
            title = clean_label(m.group(2) or m.group(3) or m.group(1))
            clusters.append(Cluster(m.group(1), title))
            stack.append(m.group(1))
            continue

        m = CLASSDEF_RE.match(line)
        if m:
            classdefs[m.group(1)] = parse_style(m.group(2))
            continue

        m = CLASS_RE.match(line)
        if m:
            for node_id in (n.strip() for n in m.group(1).split(",")):
                if node_id:
                    ensure(node_id).classes.append(m.group(2))
            continue

        m = STYLE_RE.match(line)
        if m:
            ensure(m.group(1)).style = parse_style(m.group(2))
            continue

        m = LINKSTYLE_RE.match(line)
        if m:
            decl = parse_style(m.group(2))
            for idx in (i.strip() for i in m.group(1).split(",")):
                if idx.isdigit():
                    linkstyles[int(idx)] = decl
            continue

        normalised = MID_LABEL_RE.sub(
            lambda mm: f'{mm.group(1)}{"" if mm.group(1) == "--" else "."}'
                       f'{mm.group(3).lstrip(".")}|{mm.group(2)}|',
            line,
        )
        m = EDGE_RE.match(normalised)
        if m:
            a = ensure(m.group("a"))
            b = ensure(m.group("b"))
            link = m.group("link")
            edges.append({
                "a": a.id, "b": b.id,
                "label": wrap_label(clean_label(m.group("label"))),
                "dotted": link.startswith("-."),
                "arrowhead": "triangle" if link.endswith(">") else None,
            })
            continue

        if re.match(rf'^{NODE_TOKEN}$', line):
            ensure(line)

    return nodes, edges, clusters, classdefs, linkstyles


def _cluster_by_id(clusters, cluster_id):
    for cluster in clusters:
        if cluster.id == cluster_id:
            return cluster
    raise KeyError(cluster_id)


def resolve_styles(nodes, classdefs):
    """Fold classDef/style declarations into a (stroke, fill, width) per node.

    A diagram that declares no styles at all gets the pastel palette cycled
    over its nodes; once it declares any, unstyled nodes stay neutral so the
    styled ones remain the thing that stands out.
    """
    styled_diagram = bool(classdefs) or any(n.style for n in nodes.values())
    for idx, node in enumerate(nodes.values()):
        decl = {}
        for cls in node.classes:
            decl.update(classdefs.get(cls, {}))
        if node.style:
            decl.update(node.style)
        if decl:
            stroke = decl.get("stroke", DEFAULT_STYLE[0])
            fill = decl.get("fill", DEFAULT_STYLE[1])
        elif styled_diagram:
            stroke, fill = DEFAULT_STYLE
        else:
            stroke, fill = PALETTE[idx % len(PALETTE)]
        width = decl.get("stroke-width", "2px")
        node.resolved = (stroke, fill, int(float(re.sub(r'[^\d.]', '', width) or 2)))
    return nodes


def size_node(node):
    lines = node.lines
    text_w = max(len(l) for l in lines) * LABEL_FONT * CHAR_W
    text_h = len(lines) * LABEL_FONT * LINE_H
    width = max(MIN_NODE_W, text_w + 2 * NODE_PAD_X)
    height = max(MIN_NODE_H, text_h + 2 * NODE_PAD_Y)
    if node.kind == "diamond":
        width *= DIAMOND_SCALE
        height *= DIAMOND_SCALE
    elif node.kind == "ellipse":
        width *= 1.25
        height *= 1.25
    node.width, node.height = width, height


def longest_path_columns(ids, pairs):
    """Cycle-safe longest-path depth from the roots of a directed graph.

    Edges are taken in the order given and any that would close a cycle is
    dropped, so a cyclic graph is reduced to a DAG deterministically (the
    later-declared leg of a cycle is the one that loops back) and the depths
    below describe a real flow order instead of depending on where the walk
    happened to start.
    """
    incoming = {i: set() for i in ids}
    outgoing = {i: [] for i in ids}

    def reaches(src, dst):
        stack, seen = [src], set()
        while stack:
            cur = stack.pop()
            if cur == dst:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(outgoing[cur])
        return False

    for a, b in pairs:
        if a == b or reaches(b, a):
            continue
        outgoing[a].append(b)
        incoming[b].add(a)
    col = {i: 0 for i in ids}
    roots = [i for i in ids if not incoming[i]] or list(ids)

    def visit(nid, depth, seen):
        if depth > col[nid]:
            col[nid] = depth
        if nid in seen:
            return
        seen = seen | {nid}
        for child in outgoing[nid]:
            visit(child, col[nid] + 1, seen)

    for root in roots:
        visit(root, 0, set())
    return col


def layout(nodes, edges, clusters):
    """Lay out clusters (and un-clustered nodes) into left-to-right columns.

    Every subgraph is collapsed to a single node of a cluster graph, so a
    subgraph's members always stay together in one column and the container
    boxes never interleave.
    """
    for node in nodes.values():
        size_node(node)

    # each un-clustered node becomes a cluster of one, with no container drawn
    groups = list(clusters)
    for node in nodes.values():
        if node.cluster is None:
            solo = Cluster(f"__solo_{node.id}", None)
            solo.members.append(node.id)
            node.cluster = solo.id
            groups.append(solo)

    owner = {nid: node.cluster for nid, node in nodes.items()}

    # order each cluster's members so intra-cluster edges mostly flow down
    for group in groups:
        if len(group.members) > 1:
            order = {m: i for i, m in enumerate(group.members)}
            inner = [(e["a"], e["b"]) for e in edges
                     if owner[e["a"]] == group.id and owner[e["b"]] == group.id]
            # declaration order, deduped: stable across runs, and a cycle is
            # broken at whichever edge mermaid declared last
            inner = sorted(dict.fromkeys(inner),
                           key=lambda p: (order[p[0]], order[p[1]]))
            depth = longest_path_columns(group.members, inner)
            group.members.sort(key=lambda m: (depth[m], order[m]))

    # sorted, not a set: set iteration order varies between runs and the
    # cycle-safe longest-path walk is order-sensitive, so layout must not
    # depend on it
    gorder = {g.id: i for i, g in enumerate(groups)}
    pairs = sorted({(owner[e["a"]], owner[e["b"]]) for e in edges
                    if owner[e["a"]] != owner[e["b"]]},
                   key=lambda p: (gorder[p[0]], gorder[p[1]]))
    cols = longest_path_columns([g.id for g in groups], pairs)

    # gap between two vertically adjacent members, grown to fit the label of
    # any edge joining them (the reference pulled such pairs 117-127px apart
    # for a two-line label, and left 54px where the edge had no label)
    def pair_gap(top, bottom):
        gap = NODE_GAP
        for edge in edges:
            if {edge["a"], edge["b"]} == {top, bottom} and edge["label"]:
                _, label_h = text_size(edge["label"], EDGE_LABEL_FONT)
                gap = max(gap, label_h + 2 * LABEL_PAD)
        return gap

    for group in groups:
        group.col = cols[group.id]
        group.gaps = [pair_gap(a, b)
                      for a, b in zip(group.members, group.members[1:])]
        inner_h = sum(nodes[m].height for m in group.members) + sum(group.gaps)
        inner_w = max(nodes[m].width for m in group.members)
        if group.title is None:
            group.width, group.height = inner_w, inner_h
        else:
            group.width = inner_w + 2 * CLUSTER_PAD
            group.height = inner_h + 2 * CLUSTER_PAD

    max_col = max(cols.values(), default=0)

    # the gutter between two columns must fit the widest label of an edge that
    # crosses it, plus the routing lanes either side
    gutters = {}
    for edge in edges:
        ca, cb = cols[owner[edge["a"]]], cols[owner[edge["b"]]]
        if ca == cb or not edge["label"]:
            continue
        label_w, _ = text_size(edge["label"], EDGE_LABEL_FONT)
        need = label_w + 2 * LABEL_PAD + 2 * ROUTE_MARGIN
        boundary = min(ca, cb)
        gutters[boundary] = max(gutters.get(boundary, COL_GAP), need)

    x = 0.0
    for col in range(max_col + 1):
        in_col = [g for g in groups if g.col == col]
        if not in_col:
            continue
        # a titled cluster's title now sits ABOVE its container, so the gap
        # above it has to reserve that band or the title lands on the box above
        def reserve(group):
            return 0.0 if group.title is None else TITLE_TEXT_H + TITLE_GAP

        total_h = (sum(g.height + reserve(g) for g in in_col)
                   + CLUSTER_GAP * max(0, len(in_col) - 1))
        col_w = max(g.width for g in in_col)
        y = -total_h / 2.0
        for group in in_col:
            y += reserve(group)
            group.x = x + (col_w - group.width) / 2.0
            group.y = y
            inner_x = group.x + (0 if group.title is None else CLUSTER_PAD)
            inner_w = group.width - (0 if group.title is None else 2 * CLUSTER_PAD)
            node_y = group.y + (0 if group.title is None else CLUSTER_PAD)
            for slot, member in enumerate(group.members):
                node = nodes[member]
                node.slot = slot
                node.group = group
                node.x = inner_x + (inner_w - node.width) / 2.0
                node.y = node_y
                node_y += node.height
                if slot < len(group.gaps):
                    node_y += group.gaps[slot]
            y += group.height + CLUSTER_GAP
        x += col_w + gutters.get(col, COL_GAP)
    return groups


def _base(el_id, el_type, x, y, width, height, **extra):
    el = {
        "id": el_id, "type": el_type,
        "x": x, "y": y, "width": width, "height": height,
        "angle": 0, "strokeColor": EDGE_COLOR, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": None, "seed": 1, "version": 1, "versionNonce": 1,
        "isDeleted": False, "boundElements": [], "updated": 1, "link": None,
        "locked": False,
    }
    el.update(extra)
    return el


def _text(text, x, y, width, height, color, font_size, align="center",
          valign="top", **extra):
    return _base(
        new_id(), "text", x, y, width, height,
        strokeColor=color, strokeWidth=1, text=text, originalText=text,
        fontSize=font_size, fontFamily=FONT_FAMILY, textAlign=align,
        verticalAlign=valign, containerId=None, autoResize=False,
        lineHeight=LINE_H, **extra
    )


def title_rect(group):
    """Bounding box of a cluster's title, above the container and flush left."""
    width, _ = text_size(group.title, CLUSTER_TITLE_FONT)
    return (group.x, group.y - TITLE_TEXT_H - TITLE_GAP, width, TITLE_TEXT_H)


def make_cluster(group):
    box = _base(new_id(), "rectangle", group.x, group.y, group.width, group.height,
                strokeColor=CLUSTER_STROKE, backgroundColor="transparent",
                strokeWidth=1, strokeStyle="dashed",
                roundness={"type": 3, "value": 12})
    tx, ty, tw, th = title_rect(group)
    title = _text(group.title, tx, ty, tw, th,
                  CLUSTER_TITLE_COLOR, CLUSTER_TITLE_FONT, align="left")
    return [box, title]


def make_node(node):
    stroke, fill, width = node.resolved
    shape_id = new_id()
    node.shape_id = shape_id
    label_id = new_id()
    shape = _base(
        shape_id, node.kind, node.x, node.y, node.width, node.height,
        strokeColor=stroke, backgroundColor=fill, strokeWidth=width,
        roundness=({"type": 3, "value": 8} if node.rounded
                   and node.kind == "rectangle" else None),
        boundElements=[{"type": "text", "id": label_id}],
    )
    text_h = len(node.lines) * LABEL_FONT * LINE_H
    label = _text(node.label, node.x + 5, node.y + (node.height - text_h) / 2.0,
                  node.width - 10, text_h, stroke, LABEL_FONT, valign="middle")
    label["id"] = label_id
    label["containerId"] = shape_id
    return [shape, label]


SIDES = (("l", -1, 0), ("r", 1, 0), ("t", 0, -1), ("b", 0, 1))


def _inflate(rect, margin):
    x, y, w, h = rect
    return (x - margin, y - margin, x + w + margin, y + h + margin)


def _blocked(x0, y0, x1, y1, obstacles):
    """Does the axis-aligned segment strictly cut through any obstacle?

    Rects are shrunk by 0.5 so a lane running exactly along an inflated edge
    is legal — that is the whole point of putting lanes on those edges.
    """
    lo_x, hi_x = (x0, x1) if x0 <= x1 else (x1, x0)
    lo_y, hi_y = (y0, y1) if y0 <= y1 else (y1, y0)
    for ox0, oy0, ox1, oy1 in obstacles:
        ox0, oy0, ox1, oy1 = ox0 + 0.5, oy0 + 0.5, ox1 - 0.5, oy1 - 0.5
        if min(hi_x, ox1) > max(lo_x, ox0) or (lo_x == hi_x and ox0 < lo_x < ox1):
            if min(hi_y, oy1) > max(lo_y, oy0) or (lo_y == hi_y and oy0 < lo_y < oy1):
                return True
    return False


def _anchors(node):
    """(border point, stub point, outward direction) for each side."""
    cx, cy = node.x + node.width / 2.0, node.y + node.height / 2.0
    out = []
    for _, dx, dy in SIDES:
        bx = cx + dx * node.width / 2.0
        by = cy + dy * node.height / 2.0
        out.append(((bx, by),
                    (bx + dx * ROUTE_MARGIN, by + dy * ROUTE_MARGIN),
                    (dx, dy)))
    return out


def _shortest(start, goal, xs, ys, obstacles):
    """Dijkstra over the lane grid, cost = length + TURN_PENALTY per elbow."""
    import heapq

    xi = {v: i for i, v in enumerate(xs)}
    yi = {v: i for i, v in enumerate(ys)}
    if start[0] not in xi or start[1] not in yi:
        return None, float("inf")
    sx, sy = xi[start[0]], yi[start[1]]
    gx, gy = xi[goal[0]], yi[goal[1]]

    best = {}
    heap = [(0.0, sx, sy, 0, 0, None)]  # cost, ix, iy, dx, dy, parent-state
    parents = {}
    while heap:
        cost, ix, iy, dx, dy, parent = heapq.heappop(heap)
        state = (ix, iy, dx, dy)
        if state in best:
            continue
        best[state] = cost
        parents[state] = parent
        if (ix, iy) == (gx, gy):
            path = []
            while state is not None:
                path.append((xs[state[0]], ys[state[1]]))
                state = parents[state]
            return path[::-1], cost
        for _, ndx, ndy in SIDES:
            nix, niy = ix + ndx, iy + ndy
            if not (0 <= nix < len(xs) and 0 <= niy < len(ys)):
                continue
            x0, y0, x1, y1 = xs[ix], ys[iy], xs[nix], ys[niy]
            if _blocked(x0, y0, x1, y1, obstacles):
                continue
            step = abs(x1 - x0) + abs(y1 - y0)
            turn = TURN_PENALTY if (dx, dy) not in ((0, 0), (ndx, ndy)) else 0.0
            heapq.heappush(heap, (cost + step + turn, nix, niy, ndx, ndy, state))
    return None, float("inf")


def _collapse(points, tol=0.01):
    def same(u, v):
        return abs(u - v) <= tol

    out = [points[0]]
    for point in points[1:]:
        if same(point[0], out[-1][0]) and same(point[1], out[-1][1]):
            continue
        if len(out) >= 2:
            (x0, y0), (x1, y1) = out[-2], out[-1]
            if (same(x0, x1) and same(x1, point[0])) or \
               (same(y0, y1) and same(y1, point[1])):
                out[-1] = point
                continue
        out.append(point)
    return out


def route(a, b, obstacles, bbox):
    """Orthogonal, obstacle-avoiding route from node `a` to node `b`."""
    x0, y0, x1, y1 = bbox
    ring_xs = [x0 - ROUTE_RING, x1 + ROUTE_RING]
    ring_ys = [y0 - ROUTE_RING, y1 + ROUTE_RING]
    lane_xs = ring_xs + [c for r in obstacles for c in (r[0], r[2])]
    lane_ys = ring_ys + [c for r in obstacles for c in (r[1], r[3])]

    best_path, best_cost = None, float("inf")
    for (abp, asp, ad) in _anchors(a):
        for (bbp, bsp, bd) in _anchors(b):
            xs = sorted(set(lane_xs + [asp[0], bsp[0]]))
            ys = sorted(set(lane_ys + [asp[1], bsp[1]]))
            path, cost = _shortest(asp, bsp, xs, ys, obstacles)
            if path is None:
                continue
            # prefer anchors that face the other endpoint
            toward = (b.x + b.width / 2.0 - (a.x + a.width / 2.0),
                      b.y + b.height / 2.0 - (a.y + a.height / 2.0))
            if ad[0] * toward[0] + ad[1] * toward[1] <= 0:
                cost += 30.0
            if bd[0] * toward[0] + bd[1] * toward[1] >= 0:
                cost += 30.0
            if _FLOW_AXIS == "y":  # top-down: prefer vertical anchors
                cost += 400.0 * (abs(ad[0]) + abs(bd[0]))
            if cost < best_cost:
                best_cost = cost
                best_path = _collapse([abp] + path + [bbp])
    if best_path is None:  # nothing legal: fall back to a straight line
        return [(a.x + a.width / 2.0, a.y + a.height / 2.0),
                (b.x + b.width / 2.0, b.y + b.height / 2.0)]
    return best_path


def make_edge(a, b, edge, style, obstacles, bbox):
    points = route(a, b, obstacles, bbox)
    sx, sy = points[0]
    ex, ey = points[-1]
    stroke = style.get("stroke", EDGE_COLOR)
    width = int(float(re.sub(r'[^\d.]', '', style.get("stroke-width", "2px")) or 2))
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    arrow = _base(
        new_id(), "arrow", sx, sy, max(xs) - min(xs), max(ys) - min(ys),
        strokeColor=stroke, strokeWidth=width,
        strokeStyle="dashed" if edge["dotted"] else "solid",
        points=[[p[0] - sx, p[1] - sy] for p in points], lastCommittedPoint=None,
        startBinding={"elementId": a.shape_id, "focus": 0, "gap": 5},
        endBinding={"elementId": b.shape_id, "focus": 0, "gap": 5},
        startArrowhead=None, endArrowhead=edge["arrowhead"],
        # native excalidraw elbow arrow: our points are what the export draws,
        # and a later hand-nudge in the app re-routes orthogonally instead of
        # collapsing back to a diagonal
        elbowed=True, fixedSegments=None,
        startIsSpecial=None, endIsSpecial=None,
    )
    els = [arrow]
    if edge["label"]:
        # midpoint of the longest segment: the only place on a multi-elbow
        # route with room for the label
        seg = max(zip(points, points[1:]),
                  key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
        lx = (seg[0][0] + seg[1][0]) / 2.0
        ly = (seg[0][1] + seg[1][1]) / 2.0
        label_w, label_h = text_size(edge["label"], EDGE_LABEL_FONT)
        label = _text(
            edge["label"], lx - label_w / 2.0, ly - label_h / 2.0,
            label_w, label_h,
            EDGE_LABEL_COLOR, EDGE_LABEL_FONT, valign="middle",
        )
        label["containerId"] = arrow["id"]
        arrow["boundElements"] = [{"type": "text", "id": label["id"]}]
        els.append(label)
    return els


_FLOW_AXIS = "x"


def _transpose(nodes, groups):
    """Re-lay the LR layout as TD: each column becomes a row of groups placed
    side by side; members inside a group stack horizontally.
    """
    for group in groups:
        pad = 0 if group.title is None else CLUSTER_PAD
        members = [nodes[m] for m in group.members]
        group.width = sum(n.width for n in members) + sum(group.gaps) + 2 * pad
        group.height = max(n.height for n in members) + 2 * pad
    y = 0.0
    for col in sorted({g.col for g in groups}):
        in_row = [g for g in groups if g.col == col]
        in_row.sort(key=lambda g: g.y)
        total_w = sum(g.width for g in in_row) + CLUSTER_GAP * (len(in_row) - 1)
        row_h = max(g.height + (0 if g.title is None else TITLE_TEXT_H + TITLE_GAP)
                    for g in in_row)
        x = -total_w / 2.0
        for group in in_row:
            group.x = x
            group.y = y + (0 if group.title is None else TITLE_TEXT_H + TITLE_GAP)
            pad = 0 if group.title is None else CLUSTER_PAD
            node_x = group.x + pad
            for slot, member in enumerate(group.members):
                node = nodes[member]
                node.x = node_x
                node.y = group.y + pad + (group.height - 2 * pad - node.height) / 2.0
                node_x += node.width
                if slot < len(group.gaps):
                    node_x += group.gaps[slot]
            x += group.width + CLUSTER_GAP
        y += row_h + COL_GAP


def convert_flowchart(text):
    nodes, edges, clusters, classdefs, linkstyles = parse_flowchart(text)
    resolve_styles(nodes, classdefs)
    groups = layout(nodes, edges, clusters)
    m = DIRECTIVE_RE.search(text)
    global _FLOW_AXIS
    _FLOW_AXIS = "x"
    if m and (m.group(1) or "").upper() in ("TD", "TB"):
        _FLOW_AXIS = "y"
        _transpose(nodes, groups)

    elements = []
    for group in groups:  # containers first, so they sit behind their members
        if group.title is not None:
            elements.extend(make_cluster(group))
    for node in nodes.values():
        elements.extend(make_node(node))

    titled = [g for g in groups if g.title is not None]
    rects = [(n.x, n.y, n.width, n.height) for n in nodes.values()]
    for group in titled:
        rects.append((group.x, group.y, group.width, group.height))
        tx, ty, tw, th = title_rect(group)
        rects.append((tx, ty, tw, th))
    bbox = (min(r[0] for r in rects), min(r[1] for r in rects),
            max(r[0] + r[2] for r in rects), max(r[1] + r[3] for r in rects))

    bound = {nid: [] for nid in nodes}
    for idx, edge in enumerate(edges):
        a, b = nodes[edge["a"]], nodes[edge["b"]]
        # every box but the two endpoints blocks the route; so does any titled
        # container that belongs to neither endpoint (an edge may leave its own
        # cluster, but must not slice through a third party's) plus its title
        obstacles = [_inflate((n.x, n.y, n.width, n.height), ROUTE_MARGIN)
                     for n in nodes.values() if n is not a and n is not b]
        for group in titled:
            # a title is never a legitimate thing to cross, even for an edge
            # leaving its own cluster
            obstacles.append(_inflate(title_rect(group), ROUTE_MARGIN))
            if group.id in (a.cluster, b.cluster):
                continue
            obstacles.append(
                _inflate((group.x, group.y, group.width, group.height),
                         ROUTE_MARGIN))
        els = make_edge(a, b, edge, linkstyles.get(idx, {}), obstacles, bbox)
        elements.extend(els)
        bound[a.id].append(els[0]["id"])
        bound[b.id].append(els[0]["id"])

    by_id = {e["id"]: e for e in elements}
    for node in nodes.values():
        if bound[node.id]:
            by_id[node.shape_id]["boundElements"] += [
                {"id": aid, "type": "arrow"} for aid in bound[node.id]
            ]
    return elements
