"""mermaid `quadrantChart` -> Excalidraw 2x2 quadrant chart.

Supported syntax (a subset of mermaid's, matching its semantics):

- `title <text>`; `%%` comments and `%%{init: ...}%%` blocks are ignored.
- `x-axis <left> --> <right>` or `x-axis <left>` (right label omitted).
- `y-axis <bottom> --> <top>` or `y-axis <bottom>` (top label omitted).
- `quadrant-1..4 <text>`, numbered as mermaid does: 1 top-right, 2 top-left,
  3 bottom-left, 4 bottom-right. Any missing label is simply not drawn.
- Points as `<name>: [x, y]` with x/y in 0..1 and the origin bottom-left, so
  y is flipped into Excalidraw's top-down space. A `:::class` suffix on the
  name and any trailing `radius:`/`color:`/`stroke-*:` style spec are
  accepted and ignored.

Styling was reverse-engineered from a hand-drawn reference chart
(`quadrant-reference.excalidraw`): four equal sharp-cornered squares with a
`#1e1e1e` stroke, quadrant labels in Comic Shanns centred at the top of each
square, x-axis labels centred under each column, y-axis labels rotated 90
degrees (reading bottom to top) centred beside each row, a hand-drawn
(roughness 2) blue title pill with white Excalifont text above the chart,
and one 10px solid dot per point with a smaller label directly below it.

Deliberate departures from the reference: point positions are computed from
the mermaid coordinates rather than eyeballed, the y-axis labels get an
exact -pi/2 rotation, every quadrant and axis label shares one font size,
and each quadrant gets its own pastel tint instead of a single shared fill.
A point label that would run past the chart edge, or over another point's
dot or label, is flipped above / beside its dot instead.

Imported by convert.py; not meant to be run directly.
"""
import math
import re

from convert import _base, new_id  # noqa: E402  (sibling module)

QUAD_FONT_FAMILY = 8          # Comic Shanns, as in the reference labels
QUAD_TITLE_FONT_FAMILY = 5    # Excalifont, as in the reference title
QUAD_SIZE = 165.5             # one quadrant's side; the chart is 2x2 of these
QUAD_LABEL_FONT = 10.6        # quadrant and axis labels, all one size
QUAD_LABEL_PAD_Y = 4.0        # chart edge -> quadrant / axis label
QUAD_LABEL_INSET = 0.94       # max quadrant label width as a share of QUAD_SIZE
QUAD_LABEL_MIN_FONT = 7.0     # a long quadrant label may shrink to this
QUAD_AXIS_GAP = 4.0           # chart edge -> axis label
QUAD_DOT = 10.1
QUAD_POINT_FONT = 8.4
QUAD_POINT_GAP = 1.0          # dot -> its label (below/above)
QUAD_POINT_GAP_X = 3.0        # dot -> its label (left/right)
QUAD_DIVIDER_PAD = 2.0        # a label this close to a divider counts as crossing it
QUAD_CHAR_W = 0.55            # * font size, same heuristic as the UML path
QUAD_TITLE_FONT = 11.8
QUAD_TITLE_H = 23.5
QUAD_TITLE_PAD_X = 18.0
QUAD_TITLE_GAP_Y = 21.0       # pill bottom -> chart top
QUAD_TITLE_FILL = "#228be6"
QUAD_TITLE_TEXT = "#ffffff"
QUAD_BORDER = "#1e1e1e"
QUAD_TEXT = "#1e1e1e"
# tints in mermaid's quadrant order: 1 top-right, 2 top-left, 3 bottom-left,
# 4 bottom-right (the gantt band tints)
QUAD_TINTS = ("#ebfbee", "#e7f5ff", "#fff9db", "#fff5f5")
# (column, row) of each quadrant on the 2x2 grid, in mermaid's order
QUAD_CELLS = ((1, 0), (0, 0), (0, 1), (1, 1))

INIT_RE = re.compile(r'%%\{.*?\}%%', re.S)
AXIS_RE = re.compile(r'^([xy])-axis\s+(.*?)(?:\s*-->\s*(.*?))?\s*$')
QUADRANT_RE = re.compile(r'^quadrant-([1-4])\s+(.*)$')
POINT_RE = re.compile(
    r'^(.+?)(?::::[\w-]+)?\s*:\s*\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]'
)


def parse_quadrant(text):
    """Return (title, x_labels, y_labels, quadrant_labels, points).

    `x_labels` is (left, right), `y_labels` is (bottom, top),
    `quadrant_labels` is indexed 0..3 for quadrant-1..4 and `points` is
    [(name, x, y), ...] in mermaid's bottom-left-origin unit square. Any
    label may be None.
    """
    title = None
    x_labels, y_labels = [None, None], [None, None]
    quadrants = [None] * 4
    points = []
    for raw in INIT_RE.sub("", text).splitlines():
        line = raw.split("%%", 1)[0].strip()
        if not line or line.startswith("quadrantChart"):
            continue
        if line.startswith("title "):
            title = line[6:].strip()
            continue
        m = AXIS_RE.match(line)
        if m:
            target = x_labels if m.group(1) == "x" else y_labels
            target[0] = m.group(2).strip() or None
            target[1] = (m.group(3) or "").strip() or None
            continue
        m = QUADRANT_RE.match(line)
        if m:
            quadrants[int(m.group(1)) - 1] = m.group(2).strip() or None
            continue
        m = POINT_RE.match(line)
        if m:
            x = min(max(float(m.group(2)), 0.0), 1.0)
            y = min(max(float(m.group(3)), 0.0), 1.0)
            points.append((m.group(1).strip(), x, y))
    return title, tuple(x_labels), tuple(y_labels), quadrants, points


def _text(text, x, y, width, font_size, group_ids, family=QUAD_FONT_FAMILY,
          color=QUAD_TEXT, angle=0):
    return _base(
        new_id(), "text", x, y, width, font_size * 1.25, group_ids,
        angle=angle, strokeColor=color, text=text, originalText=text,
        fontSize=font_size, fontFamily=family, textAlign="center",
        verticalAlign="top", containerId=None, autoResize=False,
        lineHeight=1.25,
    )


def _centred(text, cx, cy, font_size, group_ids, angle=0):
    """A text element whose (unrotated) box is centred on (cx, cy).

    Excalidraw rotates about the box centre, so a rotated label placed this
    way still sits centred on the point it was given.
    """
    w = len(text) * font_size * QUAD_CHAR_W
    h = font_size * 1.25
    return _text(text, cx - w / 2, cy - h / 2, w, font_size, group_ids,
                 angle=angle)


def _overlaps(a, b):
    """True when two (x0, y0, x1, y1) boxes intersect."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _label_slots(cx, cy, w, h):
    """Candidate label boxes around a dot centred on (cx, cy), in preference
    order: below, above, right, left."""
    r = QUAD_DOT / 2
    return (
        (cx - w / 2, cy + r + QUAD_POINT_GAP, cx + w / 2, cy + r + QUAD_POINT_GAP + h),
        (cx - w / 2, cy - r - QUAD_POINT_GAP - h, cx + w / 2, cy - r - QUAD_POINT_GAP),
        (cx + r + QUAD_POINT_GAP_X, cy - h / 2, cx + r + QUAD_POINT_GAP_X + w, cy + h / 2),
        (cx - r - QUAD_POINT_GAP_X - w, cy - h / 2, cx - r - QUAD_POINT_GAP_X, cy + h / 2),
    )


def _crosses_divider(box, chart):
    """True when a box straddles the chart's vertical or horizontal midline."""
    mx = (chart[0] + chart[2]) / 2
    my = (chart[1] + chart[3]) / 2
    pad = QUAD_DIVIDER_PAD
    return box[0] - pad < mx < box[2] + pad or box[1] - pad < my < box[3] + pad


def _place_labels(dots, chart):
    """Pick a label box per dot that stays inside `chart` and clear of every
    other dot and every label already placed, preferring one that does not
    straddle a quadrant divider. Falls back to "below" when nothing fits.

    `dots` is [(name, cx, cy)]; returns a parallel list of boxes.
    """
    h = QUAD_POINT_FONT * 1.25
    r = QUAD_DOT / 2
    dot_boxes = [(cx - r, cy - r, cx + r, cy + r) for _, cx, cy in dots]
    taken = []
    boxes = []
    for i, (name, cx, cy) in enumerate(dots):
        w = len(name) * QUAD_POINT_FONT * QUAD_CHAR_W
        slots = _label_slots(cx, cy, w, h)
        others = dot_boxes[:i] + dot_boxes[i + 1:]
        fits = [
            slot for slot in slots
            if slot[0] >= chart[0] and slot[1] >= chart[1]
            and slot[2] <= chart[2] and slot[3] <= chart[3]
            and not any(_overlaps(slot, b) for b in taken + others)
        ]
        tidy = [slot for slot in fits if not _crosses_divider(slot, chart)]
        chosen = (tidy or fits or slots)[0]
        taken.append(chosen)
        boxes.append(chosen)
    return boxes


def convert_quadrant(mermaid_text):
    title, x_labels, y_labels, quadrants, points = parse_quadrant(mermaid_text)
    x0, y0 = 0.0, 0.0
    size = QUAD_SIZE
    chart = (x0, y0, x0 + 2 * size, y0 + 2 * size)

    squares, quad_labels = [], []
    for label, tint, (col, row) in zip(quadrants, QUAD_TINTS, QUAD_CELLS):
        qx, qy = x0 + col * size, y0 + row * size
        squares.append(_base(new_id(), "rectangle", qx, qy, size, size, [],
                             backgroundColor=tint, roundness=None))
        if not label:
            continue
        font = QUAD_LABEL_FONT
        w = len(label) * font * QUAD_CHAR_W
        if w > size * QUAD_LABEL_INSET:  # shrink rather than spill into the neighbour
            font = max(QUAD_LABEL_MIN_FONT, font * size * QUAD_LABEL_INSET / w)
            w = len(label) * font * QUAD_CHAR_W
        quad_labels.append(_text(label, qx + (size - w) / 2, qy + QUAD_LABEL_PAD_Y,
                                 w, font, []))

    axis_labels = []
    ly = chart[3] + QUAD_AXIS_GAP + QUAD_LABEL_FONT * 1.25 / 2
    for label, col in zip(x_labels, (0, 1)):
        if label:
            axis_labels.append(_centred(label, x0 + (col + 0.5) * size, ly,
                                        QUAD_LABEL_FONT, []))
    lx = chart[0] - QUAD_AXIS_GAP - QUAD_LABEL_FONT * 1.25 / 2
    for label, row in zip(y_labels, (1, 0)):  # bottom label first, as declared
        if label:
            axis_labels.append(_centred(label, lx, y0 + (row + 0.5) * size,
                                        QUAD_LABEL_FONT, [], angle=-math.pi / 2))

    dots = [(name, x0 + px * 2 * size, y0 + (1 - py) * 2 * size)
            for name, px, py in points]
    point_els = []
    for (name, cx, cy), box in zip(dots, _place_labels(dots, chart)):
        gid = [new_id()]
        r = QUAD_DOT / 2
        point_els.append(_base(new_id(), "ellipse", cx - r, cy - r, QUAD_DOT, QUAD_DOT,
                               gid, backgroundColor=QUAD_BORDER,
                               roundness={"type": 2}))
        point_els.append(_text(name, box[0], box[1], box[2] - box[0],
                               QUAD_POINT_FONT, gid))

    title_els = []
    if title:
        gid = [new_id()]
        tw = len(title) * QUAD_TITLE_FONT * 0.57
        pill_w = tw + 2 * QUAD_TITLE_PAD_X
        px = x0 + size - pill_w / 2
        py = y0 - QUAD_TITLE_GAP_Y - QUAD_TITLE_H
        title_els.append(_base(new_id(), "rectangle", px, py, pill_w, QUAD_TITLE_H, gid,
                               strokeColor="transparent",
                               backgroundColor=QUAD_TITLE_FILL,
                               roughness=2, roundness={"type": 3}))
        title_els.append(_text(title, px + QUAD_TITLE_PAD_X,
                               py + (QUAD_TITLE_H - QUAD_TITLE_FONT * 1.25) / 2,
                               tw, QUAD_TITLE_FONT, gid,
                               family=QUAD_TITLE_FONT_FAMILY, color=QUAD_TITLE_TEXT))

    # draw order: squares, quadrant labels, axis labels, points, title
    return squares + quad_labels + axis_labels + point_els + title_els
