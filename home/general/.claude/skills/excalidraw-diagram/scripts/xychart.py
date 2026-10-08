#!/usr/bin/env python3
"""mermaid `xychart-beta` -> Excalidraw bar/line chart.

Parses `title`, `x-axis` (category list or `min --> max`), `y-axis "label"
min --> max`, any number of `bar [..]` / `line [..]` series and the optional
`horizontal` keyword. Renders clean (roughness 0) axes with tick labels and a
light grid, grouped bars with value labels, polylines with dot markers and a
swatch legend. Mermaid has no legend syntax, so series names come from
`--legend "a,b,c"`; unnamed series are "series 1..n".

Usage: xychart.py <input.mmd> <output.excalidraw> [--legend "name1,name2"]
"""
import argparse
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from convert import _base, document, new_id  # noqa: E402  (sibling module)

FONT_FAMILY = 3            # monospace, as in the skill's modern style
CHAR_W = 0.6               # * font size, Excalidraw's mono face
TITLE_FONT = 20.0
TITLE_COLOR = '#1e40af'
AXIS_FONT = 16.0
VALUE_FONT = 14.0
LEGEND_FONT = 16.0
TEXT_COLOR = '#374151'
AXIS_COLOR = '#1e3a5f'
GRID_COLOR = '#e2e8f0'
LINE_H = 1.25

PLOT_H = 320.0             # value-axis length
MIN_PLOT_W = 480.0
BAR_MIN_W = 40.0
BAR_GAP = 4.0              # between bars of one group
GROUP_PAD = 36.0           # left+right padding inside a category slot
TICK_LEN = 6.0
TICK_PAD = 8.0             # tick label -> axis
AXIS_LABEL_GAP = 16.0      # axis label -> tick labels
TITLE_GAP = 28.0
LEGEND_GAP_X = 40.0
LEGEND_SWATCH = 18.0
LEGEND_PAD_X = 10.0
LEGEND_STRIDE = 30.0
VALUE_LABEL_GAP = 6.0
MARKER_R = 5.0
MAX_VALUE_LABEL_CATS = 12

# (fill, stroke) pairs from references/color-palette.md
PALETTE = [
    ('#3b82f6', '#1e3a5f'),   # primary blue
    ('#fed7aa', '#c2410c'),   # start/trigger orange
    ('#a7f3d0', '#047857'),   # end/success green
    ('#ddd6fe', '#6d28d9'),   # AI purple
    ('#fef3c7', '#b45309'),   # decision yellow
    ('#fecaca', '#b91c1c'),   # error red
]

RANGE_RE = re.compile(r'^(?:"([^"]*)"\s*)?(-?\d+(?:\.\d+)?)\s*-->\s*(-?\d+(?:\.\d+)?)$')
LIST_RE = re.compile(r'^(?:"([^"]*)"\s*)?\[(.*)\]$')
LABEL_ONLY_RE = re.compile(r'^"([^"]*)"$')


class Chart:
    def __init__(self):
        self.title = None
        self.horizontal = False
        self.categories = []
        self.x_label = None
        self.y_label = None
        self.y_min = None
        self.y_max = None
        self.series = []   # (kind, [value tokens as str], [floats])


def _split_list(body):
    items = []
    # split on commas that are not inside double quotes
    for raw in re.findall(r'\s*"[^"]*"|[^,]+', body):
        item = raw.strip()
        if not item:
            continue
        if item[0] == item[-1] == '"':
            item = item[1:-1]
        items.append(item)
    return items


def _decimals(step):
    for d in range(0, 7):
        if abs(round(step, d) - step) < 1e-9:
            return d
    return 6


def _fmt_axis(v, step):
    if step >= 1 and float(v).is_integer():
        return f'{int(v):,}'
    return f'{v:.{_decimals(step)}f}'


def parse_xychart(text):
    chart = Chart()
    for raw in text.splitlines():
        line = raw.split('%%', 1)[0].strip()
        if not line:
            continue
        if line.startswith('xychart-beta'):
            chart.horizontal = 'horizontal' in line
            continue
        if line == 'horizontal':
            chart.horizontal = True
            continue
        if line.startswith('title'):
            title = line[5:].strip()
            chart.title = title[1:-1] if title[:1] == '"' else title
            continue
        key, _, rest = line.partition(' ')
        rest = rest.strip()
        if key == 'x-axis':
            m = LIST_RE.match(rest)
            if m:
                chart.x_label = m.group(1)
                chart.categories = _split_list(m.group(2))
                continue
            m = RANGE_RE.match(rest)
            if m:
                chart.x_label = m.group(1)
                chart.categories = (float(m.group(2)), float(m.group(3)))
                continue
            m = LABEL_ONLY_RE.match(rest)
            if m:
                chart.x_label = m.group(1)
            continue
        if key == 'y-axis':
            m = RANGE_RE.match(rest)
            if m:
                chart.y_label = m.group(1)
                chart.y_min, chart.y_max = float(m.group(2)), float(m.group(3))
                continue
            m = LABEL_ONLY_RE.match(rest)
            if m:
                chart.y_label = m.group(1)
            continue
        if key in ('bar', 'line'):
            m = LIST_RE.match(rest)
            if m:
                tokens = _split_list(m.group(2))
                chart.series.append((key, tokens, [float(t) for t in tokens]))
    if not chart.series:
        raise ValueError('xychart has no bar or line series')
    n = max(len(s[2]) for s in chart.series)
    if isinstance(chart.categories, tuple):
        lo, hi = chart.categories
        step = (hi - lo) / max(1, n - 1)
        chart.categories = [_fmt_axis(lo + i * step, step or 1) for i in range(n)]
    elif not chart.categories:
        chart.categories = [str(i + 1) for i in range(n)]
    return chart


def _nice_step(span, target=6):
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    for mult in (1, 2, 2.5, 5, 10):
        if raw <= mult * mag:
            return mult * mag
    return 10 * mag


def _ticks(lo, hi):
    """Tick values covering [lo, hi]; the last tick is at or above hi."""
    step = _nice_step(hi - lo)
    first = math.floor(lo / step + 1e-9) * step
    last = math.ceil(hi / step - 1e-9) * step
    n = int(round((last - first) / step))
    return [round(first + i * step, 10) for i in range(n + 1)], step


def _fmt_value(token, value):
    if value.is_integer() and '.' not in token:
        return f'{int(value):,}'
    return token


def _wrap(label, max_chars):
    if len(label) <= max_chars or ' ' not in label:
        return [label]
    words = label.split(' ')
    lines, cur = [], ''
    for w in words:
        cand = f'{cur} {w}'.strip()
        if cur and len(cand) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def _text(text, x, y, width, font, align, color=TEXT_COLOR, angle=0.0):
    lines = text.count('\n') + 1
    return _base(
        new_id(), 'text', x, y, width, font * LINE_H * lines, [],
        strokeColor=color, backgroundColor='transparent', angle=angle,
        text=text, originalText=text, fontSize=font, fontFamily=FONT_FAMILY,
        textAlign=align, verticalAlign='top', containerId=None,
        autoResize=False, lineHeight=LINE_H,
    )


def _line(points, color, width=1, dashed=False, fill='transparent'):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ox, oy = points[0]
    rel = [[px - ox, py - oy] for px, py in points]
    return _base(
        new_id(), 'line', ox, oy, max(xs) - min(xs), max(ys) - min(ys), [],
        strokeColor=color, backgroundColor=fill, fillStyle='solid',
        strokeWidth=width, strokeStyle='dashed' if dashed else 'solid',
        points=rel, lastCommittedPoint=None, startBinding=None,
        endBinding=None, startArrowhead=None, endArrowhead=None,
        polygon=False, boundElements=None,
    )


def _rect(x, y, w, h, fill, stroke):
    return _base(new_id(), 'rectangle', x, y, w, h, [],
                 strokeColor=stroke, backgroundColor=fill, fillStyle='solid',
                 strokeWidth=1)


def _dot(cx, cy, fill, stroke):
    return _base(new_id(), 'ellipse', cx - MARKER_R, cy - MARKER_R,
                 2 * MARKER_R, 2 * MARKER_R, [],
                 strokeColor=stroke, backgroundColor=fill, fillStyle='solid',
                 strokeWidth=1)


def convert_xychart(mermaid_text, legend_names=None):
    chart = parse_xychart(mermaid_text)
    cats = chart.categories
    n_cat = len(cats)
    bars = [s for s in chart.series if s[0] == 'bar']
    n_bar = len(bars)
    all_vals = [v for s in chart.series for v in s[2]]
    lo = 0.0 if chart.y_min is None else min(chart.y_min, 0.0, min(all_vals))
    hi = max(all_vals) if chart.y_max is None else max(chart.y_max, max(all_vals))
    if hi <= lo:
        hi = lo + 1.0
    ticks, step = _ticks(lo, hi)
    lo, hi = ticks[0], ticks[-1]
    show_values = n_cat <= MAX_VALUE_LABEL_CATS

    names = list(legend_names or [])
    for i in range(len(chart.series)):
        if i >= len(names) or not names[i]:
            names[i:i + 1] = [f'series {i + 1}']
    show_legend = legend_names is not None and len(chart.series) > 0

    # --- sizing along the category axis ---------------------------------
    value_labels = [[_fmt_value(t, v) for t, v in zip(s[1], s[2])] for s in chart.series]
    widest_value = max((len(l) for labels in value_labels for l in labels), default=1)
    bar_w = max(BAR_MIN_W, widest_value * VALUE_FONT * CHAR_W + 8)
    group_w = n_bar * bar_w + max(0, n_bar - 1) * BAR_GAP if n_bar else bar_w
    slot_w = group_w + GROUP_PAD
    if chart.horizontal:
        slot_w = max(slot_w, AXIS_FONT * LINE_H * 2 + 12)
        max_chars = 999
    else:
        min_slot = max(slot_w, MIN_PLOT_W / n_cat)
        max_chars = max(14, int(min_slot / (AXIS_FONT * CHAR_W)) - 1)
    wrapped = [_wrap(c, max_chars) for c in cats]
    if not chart.horizontal:
        widest_cat = max(len(l) for w in wrapped for l in w)
        slot_w = max(slot_w, widest_cat * AXIS_FONT * CHAR_W + 32)
    plot_w = max(MIN_PLOT_W, n_cat * slot_w)
    slot_w = plot_w / n_cat
    if n_bar == 1:
        bar_w = max(bar_w, min(slot_w * 0.55, 90.0))
        group_w = bar_w

    if chart.horizontal:
        val_len = max(MIN_PLOT_W, PLOT_H + 160.0)
        axis_w, axis_h = val_len, plot_w
    else:
        val_len = max(PLOT_H, min(plot_w * 0.45, 480.0))
        axis_w, axis_h = plot_w, val_len

    def to_xy(c, v):
        """Category-axis offset c and value v -> canvas x, y."""
        frac = (v - lo) / (hi - lo)
        if chart.horizontal:
            return frac * val_len, c
        return c, val_len - frac * val_len

    els = []
    # --- grid + value axis ticks ---------------------------------------
    tick_labels_w = max(len(_fmt_axis(t, step)) for t in ticks) * AXIS_FONT * CHAR_W
    for t in ticks:
        if chart.horizontal:
            x, _ = to_xy(0, t)
            if t != ticks[0]:
                els.append(_line([(x, 0), (x, axis_h)], GRID_COLOR, 1, dashed=True))
            els.append(_line([(x, axis_h), (x, axis_h + TICK_LEN)], AXIS_COLOR, 1))
            label = _fmt_axis(t, step)
            w = len(label) * AXIS_FONT * CHAR_W
            els.append(_text(label, x - w / 2, axis_h + TICK_LEN + TICK_PAD, w,
                             AXIS_FONT, 'center'))
        else:
            _, y = to_xy(0, t)
            if t != ticks[0]:
                els.append(_line([(0, y), (axis_w, y)], GRID_COLOR, 1, dashed=True))
            els.append(_line([(-TICK_LEN, y), (0, y)], AXIS_COLOR, 1))
            label = _fmt_axis(t, step)
            els.append(_text(label, -TICK_LEN - TICK_PAD - tick_labels_w,
                             y - AXIS_FONT * LINE_H / 2, tick_labels_w,
                             AXIS_FONT, 'right'))

    # --- axes --------------------------------------------------------------
    els.append(_line([(0, 0), (0, axis_h)], AXIS_COLOR, 2))
    els.append(_line([(0, axis_h), (axis_w, axis_h)], AXIS_COLOR, 2))

    # --- category tick labels -----------------------------------------
    cat_label_h = 0.0
    for i, lines in enumerate(wrapped):
        label = '\n'.join(lines)
        c = (i + 0.5) * slot_w
        if chart.horizontal:
            w = max(len(l) for l in lines) * AXIS_FONT * CHAR_W
            h = AXIS_FONT * LINE_H * len(lines)
            els.append(_text(label, -TICK_LEN - TICK_PAD - w, c - h / 2, w,
                             AXIS_FONT, 'right'))
            cat_label_h = max(cat_label_h, w)
        else:
            w = max(len(l) for l in lines) * AXIS_FONT * CHAR_W
            h = AXIS_FONT * LINE_H * len(lines)
            els.append(_text(label, c - w / 2, axis_h + TICK_LEN + TICK_PAD, w,
                             AXIS_FONT, 'center'))
            cat_label_h = max(cat_label_h, h)

    # --- bars ------------------------------------------------------------
    bar_idx = 0
    for s_idx, (kind, tokens, vals) in enumerate(chart.series):
        if kind != 'bar':
            continue
        fill, stroke = PALETTE[s_idx % len(PALETTE)]
        for i, v in enumerate(vals[:n_cat]):
            c0 = (i + 0.5) * slot_w - group_w / 2 + bar_idx * (bar_w + BAR_GAP)
            if chart.horizontal:
                x0, _ = to_xy(0, lo)
                x1, _ = to_xy(0, v)
                els.append(_rect(x0, c0, max(x1 - x0, 0.5), bar_w, fill, stroke))
                if show_values:
                    label = value_labels[s_idx][i]
                    w = len(label) * VALUE_FONT * CHAR_W
                    els.append(_text(label, x1 + VALUE_LABEL_GAP,
                                     c0 + bar_w / 2 - VALUE_FONT * LINE_H / 2,
                                     w, VALUE_FONT, 'left'))
            else:
                _, y0 = to_xy(0, lo)
                _, y1 = to_xy(0, v)
                els.append(_rect(c0, y1, bar_w, max(y0 - y1, 0.5), fill, stroke))
                if show_values:
                    label = value_labels[s_idx][i]
                    w = len(label) * VALUE_FONT * CHAR_W
                    els.append(_text(label, c0 + bar_w / 2 - w / 2,
                                     y1 - VALUE_LABEL_GAP - VALUE_FONT * LINE_H,
                                     w, VALUE_FONT, 'center'))
        bar_idx += 1

    # --- lines -----------------------------------------------------------
    for s_idx, (kind, tokens, vals) in enumerate(chart.series):
        if kind != 'line':
            continue
        fill, stroke = PALETTE[s_idx % len(PALETTE)]
        pts = [to_xy((i + 0.5) * slot_w, v) for i, v in enumerate(vals[:n_cat])]
        if len(pts) > 1:
            els.append(_line(pts, stroke, 2))
        for (px, py), label in zip(pts, value_labels[s_idx]):
            els.append(_dot(px, py, fill, stroke))
            if show_values and not bars:
                w = len(label) * VALUE_FONT * CHAR_W
                # alternate above/below the marker per series so labels of
                # lines that run close together do not overprint
                below = py + MARKER_R + VALUE_LABEL_GAP
                fits_below = below + VALUE_FONT * LINE_H < axis_h - TICK_PAD
                if s_idx % 2 == 0 or not fits_below:
                    ly = py - MARKER_R - VALUE_LABEL_GAP - VALUE_FONT * LINE_H
                else:
                    ly = below
                els.append(_text(label, px - w / 2, ly, w, VALUE_FONT, 'center'))

    # --- axis titles -------------------------------------------------------
    left_extent = TICK_LEN + TICK_PAD + (cat_label_h if chart.horizontal else tick_labels_w)
    bottom_extent = TICK_LEN + TICK_PAD + (AXIS_FONT * LINE_H if chart.horizontal else cat_label_h)
    v_label = chart.y_label
    c_label = chart.x_label
    left_title, bottom_title = (c_label, v_label) if chart.horizontal else (v_label, c_label)
    if bottom_title:
        w = len(bottom_title) * AXIS_FONT * CHAR_W
        els.append(_text(bottom_title, axis_w / 2 - w / 2,
                         axis_h + bottom_extent + AXIS_LABEL_GAP, w, AXIS_FONT,
                         'center', color='#64748b'))
        bottom_extent += AXIS_LABEL_GAP + AXIS_FONT * LINE_H
    if left_title:
        w = len(left_title) * AXIS_FONT * CHAR_W
        h = AXIS_FONT * LINE_H
        cx = -left_extent - AXIS_LABEL_GAP - h / 2
        cy = axis_h / 2
        els.append(_text(left_title, cx - w / 2, cy - h / 2, w, AXIS_FONT,
                         'center', color='#64748b', angle=-math.pi / 2))
        left_extent += AXIS_LABEL_GAP + h

    # --- legend ------------------------------------------------------------
    right_edge = axis_w
    if show_legend:
        lx = axis_w + LEGEND_GAP_X
        ly = 0.0
        legend_w = 0.0
        for s_idx, (kind, _, _) in enumerate(chart.series):
            fill, stroke = PALETTE[s_idx % len(PALETTE)]
            name = names[s_idx]
            w = len(name) * LEGEND_FONT * CHAR_W
            legend_w = max(legend_w, LEGEND_SWATCH + LEGEND_PAD_X + w)
            sy = ly + (LEGEND_STRIDE - LEGEND_SWATCH) / 2
            if kind == 'bar':
                els.append(_rect(lx, sy, LEGEND_SWATCH, LEGEND_SWATCH, fill, stroke))
            else:
                mid = sy + LEGEND_SWATCH / 2
                els.append(_line([(lx, mid), (lx + LEGEND_SWATCH, mid)], stroke, 2))
                els.append(_dot(lx + LEGEND_SWATCH / 2, mid, fill, stroke))
            els.append(_text(name, lx + LEGEND_SWATCH + LEGEND_PAD_X,
                             ly + (LEGEND_STRIDE - LEGEND_FONT * LINE_H) / 2, w,
                             LEGEND_FONT, 'left'))
            ly += LEGEND_STRIDE
        right_edge = lx + legend_w

    # --- title -------------------------------------------------------------
    if chart.title:
        w = len(chart.title) * TITLE_FONT * CHAR_W
        left = -left_extent
        els.append(_text(chart.title, (left + right_edge) / 2 - w / 2,
                         -TITLE_GAP - TITLE_FONT * LINE_H - VALUE_FONT * LINE_H, w,
                         TITLE_FONT, 'center', color=TITLE_COLOR))
    return els


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--legend', default=None,
                    help='comma-separated series names, in source order')
    args = ap.parse_args()
    with open(args.input) as f:
        text = f.read()
    legend = None
    if args.legend is not None:
        legend = [s.strip() for s in args.legend.split(',')]
    doc = document(convert_xychart(text, legend))
    with open(args.output, 'w') as f:
        json.dump(doc, f, indent=2)


if __name__ == '__main__':
    main()
