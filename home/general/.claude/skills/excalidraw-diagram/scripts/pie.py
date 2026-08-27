"""mermaid `pie` -> Excalidraw pie chart.

Styling was reverse-engineered from a hand-drawn reference pie
(`example-pie.excalidraw`): a roughness-1 ellipse holding the last slice's
fill, one solid-filled `line` wedge per remaining slice (centre -> rim -> arc
samples -> centre, so a hand-nudge in the app keeps the wedge closed), a
percentage label inside each slice and a swatch+label legend to the right of
the circle.
"""
import math
import re

from convert import _base, new_id  # noqa: E402  (sibling module)

PIE_FONT_FAMILY = 8          # Comic Shanns, as elsewhere in this skill
PIE_TITLE_FONT_FAMILY = 5    # Excalifont, as in the gantt title
PIE_RADIUS = 205.0 / 2       # reference circle is 205px across
PIE_ARC_STEP = 4.0           # degrees between arc samples
PIE_CHAR_W = 0.55            # * font size, same heuristic as the UML path
PIE_SLICE_FONT = 16.0
PIE_SLICE_MIN_FONT = 11.0    # narrow slices shrink their % label to this floor
PIE_SLICE_LABEL_R = 0.62     # * radius, where the % label sits
PIE_SLICE_LABEL_R_MAX = 0.76  # * radius, how far out a narrow slice's label may go
PIE_MIN_LABEL_SWEEP = 8.0    # degrees; below this the % label is dropped
PIE_LEGEND_FONT = 18.18
PIE_LEGEND_GAP_X = 46.0      # circle rim -> legend swatch
PIE_LEGEND_SWATCH = 20.0
PIE_LEGEND_PAD_X = 12.0      # swatch -> its label
PIE_LEGEND_STRIDE = 30.0
PIE_TITLE_FONT = 25.82
PIE_TITLE_GAP_Y = 28.0
PIE_BORDER = "#000000"       # as in the reference
PIE_TEXT = "#1e1e1e"
PIE_PALETTE = [
    "#a5d8ff",
    "#b2f2bb",
    "#ffec99",
    "#ffc9c9",
    "#d0bfff",
    "#ffd8a8",
    "#99e9f2",
    "#eebefa",
    "#ced4da",
]

SLICE_RE = re.compile(r'^"([^"]*)"\s*:\s*(-?\d+(?:\.\d+)?)$')


def parse_pie(text):
    """Return (title, show_data, [(label, value), ...])."""
    title = None
    show_data = False
    slices = []
    for raw in text.splitlines():
        line = raw.split("%%", 1)[0].strip()
        if not line:
            continue
        if line.startswith("pie"):
            show_data = "showData" in line
            continue
        if line.startswith("title "):
            title = line[6:].strip()
            continue
        m = SLICE_RE.match(line)
        if m:
            slices.append((m.group(1), float(m.group(2))))
    if not slices:
        raise ValueError("pie diagram has no slices")
    return title, show_data, slices


def _text(text, x, y, width, font_size, align, group_ids, family=PIE_FONT_FAMILY,
          background="transparent"):
    lines = text.count("\n") + 1
    return _base(
        new_id(), "text", x, y, width, font_size * 1.25 * lines, group_ids,
        strokeColor=PIE_TEXT, backgroundColor=background,
        text=text, originalText=text, fontSize=font_size, fontFamily=family,
        textAlign=align, verticalAlign="top", containerId=None,
        autoResize=False, lineHeight=1.25,
    )


def _rim(cx, cy, r, angle):
    """Point on the circle at `angle` degrees clockwise from 12 o'clock."""
    a = math.radians(angle)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def _arc(cx, cy, r, a0, a1):
    """Samples along the rim from a0 to a1, both endpoints included."""
    n = max(1, int(math.ceil((a1 - a0) / PIE_ARC_STEP)))
    return [_rim(cx, cy, r, a0 + (a1 - a0) * i / n) for i in range(n + 1)]


def _wedge(cx, cy, r, a0, a1, fill, group_ids):
    pts = [(cx, cy)] + _arc(cx, cy, r, a0, a1) + [(cx, cy)]
    ox, oy = pts[0]
    rel = [[px - ox, py - oy] for px, py in pts]
    xs = [p[0] for p in rel]
    ys = [p[1] for p in rel]
    return _base(
        new_id(), "line", ox, oy, max(xs) - min(xs), max(ys) - min(ys), group_ids,
        strokeColor=PIE_BORDER, backgroundColor=fill, fillStyle="solid",
        strokeWidth=1, roughness=1, points=rel, lastCommittedPoint=None,
        startBinding=None, endBinding=None,
        startArrowhead=None, endArrowhead=None, polygon=False,
    )


def convert_pie(mermaid_text):
    title, show_data, slices = parse_pie(mermaid_text)
    total = sum(v for _, v in slices)
    if total <= 0:
        raise ValueError("pie slice values must sum to more than zero")

    cx = cy = 0.0
    r = PIE_RADIUS
    group_ids = [new_id()]
    colors = [PIE_PALETTE[i % len(PIE_PALETTE)] for i in range(len(slices))]

    # the ellipse sits underneath everything, so any seam between wedges shows
    # the last slice's colour rather than white
    circle = [_base(new_id(), "ellipse", cx - r, cy - r, 2 * r, 2 * r, group_ids,
                    strokeColor=PIE_BORDER, backgroundColor=colors[-1],
                    fillStyle="solid", strokeWidth=1, roughness=1)]

    wedges, labels = [], []
    angle = 0.0
    for (label, value), fill in zip(slices, colors):
        sweep = value / total * 360.0
        a0, a1 = angle, angle + sweep
        angle = a1
        if len(slices) > 1:
            wedges.append(_wedge(cx, cy, r, a0, a1, fill, group_ids))
        if sweep < PIE_MIN_LABEL_SWEEP:
            continue  # a label would not fit inside the slice
        pct = f"{value / total * 100:.0f}%"
        w = len(pct) * PIE_SLICE_FONT * PIE_CHAR_W
        # a narrow slice is only as wide as its chord, so slide the label out
        # until the chord can hold it — but never past PIE_SLICE_LABEL_R_MAX,
        # and shrink the face if even the outermost chord is still too short
        half = math.sin(math.radians(sweep / 2))
        label_r = min(max(PIE_SLICE_LABEL_R * r, w / (2 * half)),
                      PIE_SLICE_LABEL_R_MAX * r)
        font = PIE_SLICE_FONT
        chord = 2 * label_r * half
        if w > chord:
            font = max(PIE_SLICE_MIN_FONT, font * chord / w)
            w = len(pct) * font * PIE_CHAR_W
        lx, ly = _rim(cx, cy, label_r, (a0 + a1) / 2)
        labels.append(_text(pct, lx - w / 2, ly - font * 1.25 / 2, w,
                            font, "center", []))

    legend = []
    lx = cx + r + PIE_LEGEND_GAP_X
    ly = cy - len(slices) * PIE_LEGEND_STRIDE / 2
    legend_w = 0.0
    for (label, value), fill in zip(slices, colors):
        text = f"{label} — {value:g}" if show_data else label
        w = len(text) * PIE_LEGEND_FONT * PIE_CHAR_W
        legend_w = max(legend_w, PIE_LEGEND_SWATCH + PIE_LEGEND_PAD_X + w)
        sy = ly + (PIE_LEGEND_STRIDE - PIE_LEGEND_SWATCH) / 2
        legend.append(_base(new_id(), "rectangle", lx, sy,
                            PIE_LEGEND_SWATCH, PIE_LEGEND_SWATCH, [],
                            strokeColor=PIE_BORDER, backgroundColor=fill,
                            fillStyle="solid", strokeWidth=1, roundness=None))
        legend.append(_text(text, lx + PIE_LEGEND_SWATCH + PIE_LEGEND_PAD_X,
                            ly + (PIE_LEGEND_STRIDE - PIE_LEGEND_FONT * 1.25) / 2,
                            w, PIE_LEGEND_FONT, "left", []))
        ly += PIE_LEGEND_STRIDE

    title_els = []
    if title:
        left, right = cx - r, lx + legend_w
        tw = len(title) * PIE_TITLE_FONT * 0.57
        title_els.append(_text(
            title, (left + right) / 2 - tw / 2,
            cy - r - PIE_TITLE_GAP_Y - PIE_TITLE_FONT * 1.25, tw,
            PIE_TITLE_FONT, "center", [], family=PIE_TITLE_FONT_FAMILY))

    # draw order: base circle, wedges, slice labels, legend, title
    return circle + wedges + labels + legend + title_els
