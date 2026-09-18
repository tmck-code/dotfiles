"""mermaid `xychart-beta` -> Excalidraw bar / line chart.

Supported syntax (a subset of mermaid's, matching its semantics):

- `xychart-beta` optionally followed by `horizontal`; `%%` comments and
  `%%{init: ...}%%` blocks are ignored.
- `title <text>` (quoted or bare).
- `x-axis [a, b, c]`, `x-axis "label" [a, b, c]` — a categorical axis, one
  slot per entry. `x-axis "label" 0 --> 100` (a numeric range) is accepted
  and its endpoints used as evenly spaced category ticks, as mermaid does
  when no categories are given.
- `y-axis "label"`, `y-axis 0 --> 100`, `y-axis "label" 0 --> 100` — the
  value axis. Without an explicit range the range is chosen from the data,
  always including zero so bar lengths stay proportional.
- `bar [v1, v2, ...]` and `line [v1, v2, ...]`, optionally titled
  (`bar "2024" [...]`). Several series may be given: bars are grouped side
  by side within each category, lines are drawn over them with a dot per
  point. A legend appears as soon as there is more than one series.

Styling follows the other emitters in this skill: Comic Shanns axis and
value labels, a roughness-2 blue Excalifont title pill as on the quadrant
chart, and the shared bar palette used for the wedge fills in `pie.py`.

Category labels that are too wide for their slot are rotated 45 degrees so
they stay readable instead of overlapping each other.

Imported by convert.py; not meant to be run directly.
"""
import math
import re

from convert import _base, new_id  # noqa: E402  (sibling module)

BAR_FONT_FAMILY = 8           # Comic Shanns, as elsewhere in this skill
BAR_TITLE_FONT_FAMILY = 5     # Excalifont, as in the quadrant title
BAR_PLOT_W = 420.0            # plot area, before --scale
BAR_PLOT_H = 240.0
BAR_LABEL_FONT = 10.6         # category labels and axis titles
BAR_TICK_FONT = 9.5           # value-axis tick labels
BAR_CHAR_W = 0.55             # * font size, same heuristic as the UML path
BAR_TICKS = 5                 # target number of value-axis ticks
BAR_TICK_GAP = 6.0            # tick label -> value axis
BAR_CAT_GAP = 6.0             # plot edge -> category label
BAR_AXIS_TITLE_GAP = 9.0      # category labels -> axis title
BAR_SLOT_PAD = 0.16           # share of a category slot left empty each side
BAR_SERIES_GAP = 2.0          # between grouped bars in one category
BAR_ROTATE = -math.pi / 4     # tilt applied to over-wide category labels
BAR_DOT = 7.0                 # line-series point marker
BAR_LEGEND_FONT = 10.6
BAR_LEGEND_SWATCH = 13.0
BAR_LEGEND_PAD_X = 6.0        # swatch -> its label
BAR_LEGEND_GAP_X = 18.0       # between legend entries
BAR_LEGEND_GAP_Y = 14.0       # axis title -> legend row
BAR_TITLE_FONT = 11.8
BAR_TITLE_H = 23.5
BAR_TITLE_PAD_X = 18.0
BAR_TITLE_GAP_Y = 21.0        # pill bottom -> plot top
BAR_TITLE_FILL = "#228be6"
BAR_TITLE_TEXT = "#ffffff"
BAR_AXIS = "#1e1e1e"
BAR_GRID = "#ced4da"
BAR_TEXT = "#1e1e1e"
# (fill, stroke) per series, cycled; the pie palette with matching inks
BAR_PALETTE = (
    ("#a5d8ff", "#1971c2"),
    ("#b2f2bb", "#2f9e44"),
    ("#ffec99", "#f08c00"),
    ("#ffc9c9", "#e03131"),
    ("#d0bfff", "#6741d9"),
    ("#ffd8a8", "#e8590c"),
    ("#99e9f2", "#0c8599"),
    ("#eebefa", "#ae3ec9"),
)

INIT_RE = re.compile(r'%%\{.*?\}%%', re.S)
AXIS_RE = re.compile(r'^([xy])-axis\s*(.*)$')
SERIES_RE = re.compile(r'^(bar|line)\s*(.*)$')
RANGE_RE = re.compile(r'^(.*?)\s*(-?\d+(?:\.\d+)?)\s*-->\s*(-?\d+(?:\.\d+)?)\s*$')
NUM_RE = re.compile(r'^-?\d+(?:\.\d+)?$')


def _unquote(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in '"\'':
        return text[1:-1]
    return text


def _split_list(body):
    """Split the inside of a `[a, b, c]` list into stripped, unquoted items."""
    return [_unquote(p) for p in body.split(",") if p.strip()]


def _parse_axis(body):
    """Return (title, categories, value_range) for one axis line.

    Exactly one of `categories` / `value_range` is non-None, or both are
    None when the line only carries a title.
    """
    body = body.strip()
    if "[" in body and body.endswith("]"):
        head, _, rest = body.partition("[")
        return _unquote(head) or None, _split_list(rest[:-1]), None
    m = RANGE_RE.match(body)
    if m:
        return _unquote(m.group(1)) or None, None, (float(m.group(2)),
                                                    float(m.group(3)))
    return _unquote(body) or None, None, None


def parse_xychart(text):
    """Return (title, horizontal, x_title, categories, y_title, y_range,
    series).

    `series` is [(kind, label, [values]), ...] with `kind` in
    {"bar", "line"}. Any title may be None.
    """
    title = None
    horizontal = False
    x_title = y_title = None
    categories = None
    y_range = None
    series = []
    for raw in INIT_RE.sub("", text).splitlines():
        line = raw.split("%%", 1)[0].strip()
        if not line:
            continue
        if line.startswith("xychart-beta"):
            horizontal = "horizontal" in line
            continue
        if line.startswith("title "):
            title = _unquote(line[6:])
            continue
        m = AXIS_RE.match(line)
        if m:
            axis_title, cats, rng = _parse_axis(m.group(2))
            if m.group(1) == "x":
                x_title, categories = axis_title, cats
                if cats is None and rng is not None:
                    # a numeric x range with no categories: use its endpoints
                    categories = [f"{rng[0]:g}", f"{rng[1]:g}"]
            else:
                y_title, y_range = axis_title, rng
            continue
        m = SERIES_RE.match(line)
        if m:
            body = m.group(2).strip()
            label = None
            if "[" in body:
                head, _, rest = body.partition("[")
                label = _unquote(head) or None
                values = [float(v) for v in _split_list(rest.rstrip("]"))
                          if NUM_RE.match(v)]
            else:
                values = []
            if values:
                series.append((m.group(1), label, values))
            continue
    if not series:
        raise ValueError("xychart has no bar or line series")
    width = max(len(v) for _, _, v in series)
    if not categories:
        categories = [str(i + 1) for i in range(width)]
    # pad short series / ignore values past the category count
    series = [(kind, label, (vals + [0.0] * width)[:len(categories)])
              for kind, label, vals in series]
    return (title, horizontal, x_title, categories, y_title, y_range, series)


def _nice_step(span, target):
    """A 1/2/2.5/5 x 10^k step covering `span` in about `target` intervals."""
    raw = span / target
    mag = 10.0 ** math.floor(math.log10(raw))
    for mult in (1.0, 2.0, 2.5, 5.0, 10.0):
        if raw <= mult * mag:
            return mult * mag
    return 10.0 * mag


def _value_axis(series, y_range):
    """Return (lo, hi, step) for the value axis."""
    if y_range:
        lo, hi = min(y_range), max(y_range)
        if hi == lo:
            hi = lo + 1.0
        return lo, hi, _nice_step(hi - lo, BAR_TICKS)
    values = [v for _, _, vals in series for v in vals]
    lo, hi = min(values), max(values)
    lo = min(lo, 0.0)          # bars are only proportional when zero is shown
    hi = max(hi, 0.0)
    if hi == lo:
        hi = lo + 1.0
    step = _nice_step(hi - lo, BAR_TICKS)
    return (math.floor(lo / step) * step, math.ceil(hi / step) * step, step)


def _ticks(lo, hi, step):
    out, v = [], lo
    while v <= hi + step * 1e-6:
        out.append(0.0 if abs(v) < step * 1e-6 else v)
        v += step
    return out


def _text(text, x, y, width, font_size, group_ids, family=BAR_FONT_FAMILY,
          color=BAR_TEXT, align="center", angle=0):
    return _base(
        new_id(), "text", x, y, width, font_size * 1.25, group_ids,
        angle=angle, strokeColor=color, text=text, originalText=text,
        fontSize=font_size, fontFamily=family, textAlign=align,
        verticalAlign="top", containerId=None, autoResize=False,
        lineHeight=1.25,
    )


def _centred(text, cx, cy, font_size, group_ids, angle=0, family=BAR_FONT_FAMILY):
    """A text element whose (unrotated) box is centred on (cx, cy).

    Excalidraw rotates about the box centre, so a rotated label placed this
    way still sits centred on the point it was given.
    """
    w = len(text) * font_size * BAR_CHAR_W
    return _text(text, cx - w / 2, cy - font_size * 1.25 / 2, w, font_size,
                 group_ids, family=family, angle=angle)


def _line(x0, y0, x1, y1, color, width, group_ids, dashed=False):
    return _base(
        new_id(), "line", x0, y0, abs(x1 - x0), abs(y1 - y0), group_ids,
        strokeColor=color, strokeWidth=width,
        strokeStyle="dashed" if dashed else "solid", roughness=0,
        points=[[0.0, 0.0], [x1 - x0, y1 - y0]], lastCommittedPoint=None,
        startBinding=None, endBinding=None,
        startArrowhead=None, endArrowhead=None, polygon=False,
    )


def _polyline(points, color, width, group_ids):
    ox, oy = points[0]
    rel = [[px - ox, py - oy] for px, py in points]
    xs = [p[0] for p in rel]
    ys = [p[1] for p in rel]
    return _base(
        new_id(), "line", ox, oy, max(xs) - min(xs), max(ys) - min(ys),
        group_ids, strokeColor=color, strokeWidth=width, roughness=0,
        points=rel, lastCommittedPoint=None,
        startBinding=None, endBinding=None,
        startArrowhead=None, endArrowhead=None, polygon=False,
    )


def convert_bar(mermaid_text):
    (title, horizontal, x_title, categories, y_title, y_range,
     series) = parse_xychart(mermaid_text)

    lo, hi, step = _value_axis(series, y_range)
    ticks = _ticks(lo, hi, step)
    decimals = max(0, -int(math.floor(math.log10(step)))) if step < 1 else 0
    tick_text = [f"{v:.{decimals}f}" for v in ticks]

    # the plot's origin sits at (0, 0); everything else is placed around it
    x0, y0 = 0.0, 0.0
    plot_w, plot_h = BAR_PLOT_W, BAR_PLOT_H
    if horizontal:
        # a horizontal chart grows downward with the category count rather
        # than squeezing every category into a fixed height
        plot_h = max(BAR_PLOT_H, len(categories) * 34.0)
    x1, y1 = x0 + plot_w, y0 + plot_h
    gid = [new_id()]

    cat_axis_len = plot_h if horizontal else plot_w
    val_axis_len = plot_w if horizontal else plot_h
    slot = cat_axis_len / len(categories)

    def val_pos(v):
        """Position along the value axis for value `v`."""
        frac = (v - lo) / (hi - lo)
        return x0 + frac * val_axis_len if horizontal else y1 - frac * val_axis_len

    bars = [s for s in series if s[0] == "bar"]
    lines = [s for s in series if s[0] == "line"]
    band = (slot * (1 - 2 * BAR_SLOT_PAD) - BAR_SERIES_GAP * (len(bars) - 1))
    band = max(band / len(bars), 2.0) if bars else 0.0

    # one palette entry per series, bars first so a bar and the line over it
    # never share a colour; indexed by position in `series` for the legend
    colour_of, seen_bars, seen_lines = [], 0, 0
    for kind, _, _ in series:
        if kind == "bar":
            colour_of.append(BAR_PALETTE[seen_bars % len(BAR_PALETTE)])
            seen_bars += 1
        else:
            colour_of.append(
                BAR_PALETTE[(len(bars) + seen_lines) % len(BAR_PALETTE)])
            seen_lines += 1
    bar_colours = [c for c, s in zip(colour_of, series) if s[0] == "bar"]
    line_colours = [c for c, s in zip(colour_of, series) if s[0] == "line"]

    grid, bar_els, line_els = [], [], []

    # value-axis gridlines + tick labels
    tick_label_w = max(len(t) for t in tick_text) * BAR_TICK_FONT * BAR_CHAR_W
    for value, label in zip(ticks, tick_text):
        p = val_pos(value)
        zero = abs(value) < step * 1e-6
        color = BAR_AXIS if zero else BAR_GRID
        if horizontal:
            grid.append(_line(p, y0, p, y1, color, 1, gid, dashed=not zero))
            grid.append(_centred(label, p, y1 + BAR_TICK_GAP + BAR_TICK_FONT * 0.6,
                                 BAR_TICK_FONT, gid))
        else:
            grid.append(_line(x0, p, x1, p, color, 1, gid, dashed=not zero))
            grid.append(_text(label, x0 - BAR_TICK_GAP - tick_label_w,
                              p - BAR_TICK_FONT * 1.25 / 2, tick_label_w,
                              BAR_TICK_FONT, gid, align="right"))

    # the two axis spines
    grid.append(_line(x0, y0, x0, y1, BAR_AXIS, 2, gid))
    grid.append(_line(x0, y1, x1, y1, BAR_AXIS, 2, gid))

    # bars, grouped within each category slot
    base = val_pos(max(lo, min(hi, 0.0)))
    for si, (_, _, values) in enumerate(bars):
        fill, stroke = bar_colours[si]
        for ci, value in enumerate(values):
            start = (slot * ci + slot * BAR_SLOT_PAD
                     + si * (band + BAR_SERIES_GAP))
            tip = val_pos(min(max(value, lo), hi))
            if horizontal:
                bx, bw = min(base, tip), abs(tip - base)
                by, bh = y0 + start, band
            else:
                bx, bw = x0 + start, band
                by, bh = min(base, tip), abs(tip - base)
            bar_els.append(_base(
                new_id(), "rectangle", bx, by, max(bw, 0.5), max(bh, 0.5), gid,
                strokeColor=stroke, backgroundColor=fill, fillStyle="solid",
                strokeWidth=1, roughness=1, roundness=None))

    # line series over the bars, with a dot per point
    for si, (_, _, values) in enumerate(lines):
        _, stroke = line_colours[si]
        pts = []
        for ci, value in enumerate(values):
            centre = slot * ci + slot / 2
            p = val_pos(min(max(value, lo), hi))
            pts.append((p, y0 + centre) if horizontal else (x0 + centre, p))
        line_els.append(_polyline(pts, stroke, 2, gid))
        for px, py in pts:
            line_els.append(_base(
                new_id(), "ellipse", px - BAR_DOT / 2, py - BAR_DOT / 2,
                BAR_DOT, BAR_DOT, gid, strokeColor=stroke,
                backgroundColor=stroke, fillStyle="solid", strokeWidth=1,
                roughness=0))

    # category labels, tilted when they would collide
    cat_els = []
    widest = max(len(c) for c in categories) * BAR_LABEL_FONT * BAR_CHAR_W
    tilt = (not horizontal) and widest > slot
    cat_extent = 0.0
    for ci, name in enumerate(categories):
        centre = slot * ci + slot / 2
        if horizontal:
            w = len(name) * BAR_LABEL_FONT * BAR_CHAR_W
            cat_extent = max(cat_extent, w)
            cat_els.append(_text(name, x0 - BAR_CAT_GAP - w,
                                 y0 + centre - BAR_LABEL_FONT * 1.25 / 2, w,
                                 BAR_LABEL_FONT, gid, align="right"))
        elif tilt:
            # rotate about the box centre, placing the label's right-hand end
            # just under its tick so the text runs up toward the axis
            w = len(name) * BAR_LABEL_FONT * BAR_CHAR_W
            ax, ay = x0 + centre, y1 + BAR_CAT_GAP
            half = w / 2 * math.cos(BAR_ROTATE)
            cat_extent = max(cat_extent, w * abs(math.sin(BAR_ROTATE)))
            cat_els.append(_centred(name, ax - half, ay + half,
                                    BAR_LABEL_FONT, gid, angle=BAR_ROTATE))
        else:
            cat_extent = max(cat_extent, BAR_LABEL_FONT * 1.25)
            cat_els.append(_centred(name, x0 + centre,
                                    y1 + BAR_CAT_GAP + BAR_LABEL_FONT * 1.25 / 2,
                                    BAR_LABEL_FONT, gid))

    # Axis titles. Whichever axis runs along the bottom gets its title
    # centred underneath; the one running up the left gets it rotated. Which
    # is which swaps with `horizontal`, so pick the pair rather than
    # hard-coding x below and y on the left.
    axis_els = []
    if horizontal:
        below, side = y_title, x_title           # values along the bottom
        below_gap = BAR_CAT_GAP + BAR_TICK_FONT * 1.25
        side_gap = BAR_CAT_GAP + cat_extent
    else:
        below, side = x_title, y_title           # categories along the bottom
        below_gap = BAR_CAT_GAP + cat_extent
        side_gap = BAR_TICK_GAP + tick_label_w
    cat_base = y1 + below_gap + BAR_AXIS_TITLE_GAP
    if below:
        axis_els.append(_centred(below, x0 + plot_w / 2,
                                 cat_base + BAR_LABEL_FONT * 1.25 / 2,
                                 BAR_LABEL_FONT, gid))
    if side:
        left = x0 - side_gap - BAR_AXIS_TITLE_GAP
        axis_els.append(_centred(side, left - BAR_LABEL_FONT * 1.25 / 2,
                                 y0 + plot_h / 2, BAR_LABEL_FONT, gid,
                                 angle=-math.pi / 2))

    # legend, centred under the chart, only once there is more than one series
    legend_els = []
    legend_bottom = cat_base + (BAR_LABEL_FONT * 1.25 if below else 0.0)
    if len(series) > 1:
        entries = []
        for si, (kind, label, _) in enumerate(series):
            fill, stroke = colour_of[si]
            name = label or f"{kind} {si + 1}"
            w = len(name) * BAR_LEGEND_FONT * BAR_CHAR_W
            entries.append((name, fill, stroke, kind, w))
        total = sum(BAR_LEGEND_SWATCH + BAR_LEGEND_PAD_X + w
                    for _, _, _, _, w in entries)
        total += BAR_LEGEND_GAP_X * (len(entries) - 1)
        lx = x0 + plot_w / 2 - total / 2
        ly = legend_bottom + BAR_LEGEND_GAP_Y
        for name, fill, stroke, kind, w in entries:
            sy = ly + (BAR_LEGEND_FONT * 1.25 - BAR_LEGEND_SWATCH) / 2
            legend_els.append(_base(
                new_id(), "rectangle", lx, sy, BAR_LEGEND_SWATCH,
                BAR_LEGEND_SWATCH, gid, strokeColor=stroke,
                backgroundColor=fill if kind == "bar" else stroke,
                fillStyle="solid", strokeWidth=1, roughness=1, roundness=None))
            legend_els.append(_text(
                name, lx + BAR_LEGEND_SWATCH + BAR_LEGEND_PAD_X, ly, w,
                BAR_LEGEND_FONT, gid, align="left"))
            lx += BAR_LEGEND_SWATCH + BAR_LEGEND_PAD_X + w + BAR_LEGEND_GAP_X

    title_els = []
    if title:
        tw = len(title) * BAR_TITLE_FONT * 0.57
        pill_w = tw + 2 * BAR_TITLE_PAD_X
        px = x0 + plot_w / 2 - pill_w / 2
        py = y0 - BAR_TITLE_GAP_Y - BAR_TITLE_H
        title_els.append(_base(
            new_id(), "rectangle", px, py, pill_w, BAR_TITLE_H, gid,
            strokeColor="transparent", backgroundColor=BAR_TITLE_FILL,
            roughness=2, roundness={"type": 3}))
        title_els.append(_text(
            title, px + BAR_TITLE_PAD_X,
            py + (BAR_TITLE_H - BAR_TITLE_FONT * 1.25) / 2, tw,
            BAR_TITLE_FONT, gid, family=BAR_TITLE_FONT_FAMILY,
            color=BAR_TITLE_TEXT))

    # draw order: grid under bars, lines over bars, then chrome
    return grid + bar_els + line_els + cat_els + axis_els + legend_els + title_els
