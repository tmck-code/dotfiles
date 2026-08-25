"""mermaid `gantt` -> Excalidraw timeline.

Styling was reverse-engineered from a hand-converted reference gantt
(`example-gantt.excalidraw`): one tinted full-width band per section with
its wrapped title in a label column on the left, a vertical grid line per
axis unit spanning all bands, one row per task with a rounded solid bar
(width = duration * GANTT_UNIT_W), a bar label centred inside the bar or,
when the bar is too narrow, placed just to the right of it in a smaller
face over a band-tinted backing so it stays legible across grid lines, tick
labels under the bottom band and a hand-drawn (roughness 2) title pill above.
"""
import re

from convert import _base, new_id  # noqa: E402  (sibling module)

GANTT_FONT_FAMILY = 8          # Comic Shanns, as in the reference bars
GANTT_TITLE_FONT_FAMILY = 5    # Excalifont, as in the reference title
GANTT_UNIT_W = 95.0            # px per axis unit (one grid column)
GANTT_BAR_H = 31.0
GANTT_ROW_STRIDE = 31.0        # reference rows touch, no gap
GANTT_BAND_PAD_Y = 22.0
GANTT_LABEL_COL_W = 123.0      # section-label column left of the axis origin
GANTT_LABEL_PAD_X = 18.0
GANTT_BAR_FONT = 18.18
GANTT_SIDE_FONT = 13.85        # label placed beside a too-narrow bar
GANTT_SIDE_GAP_X = 6.0         # gap between bar end and its side label
GANTT_TICK_FONT = 16.62
GANTT_SECTION_FONT = 25.82
GANTT_TITLE_FONT = 25.82
GANTT_CHAR_W = 0.55            # * font size, same heuristic as the UML path
GANTT_TICK_GAP_Y = 2.0
GANTT_TITLE_GAP_Y = 25.0
GANTT_TITLE_PAD_X = 40.0
GANTT_TITLE_H = 52.0
GANTT_BORDER = "#1e1e1e"
GANTT_TEXT = "#1e1e1e"
# (bar fill, band tint) pairs, cycled per section; first two from the reference
GANTT_PALETTE = [
    ("#b2f2bb", "#ebfbee"),
    ("#a5d8ff", "#e7f5ff"),
    ("#ffec99", "#fff9db"),
    ("#ffc9c9", "#fff5f5"),
    ("#d0bfff", "#f3f0ff"),
    ("#ffd8a8", "#fff4e6"),
]

TASK_RE = re.compile(r'^(.*?)\s*:\s*(.+)$')
NUM_RE = re.compile(r'^-?\d+(?:\.\d+)?$')


def _parse_task(name, spec, prev_end, ids):
    """Return (name, start, end) from a mermaid task spec.

    Handles `[tags,] [id,] [start,] end|duration` where start is a number or
    `after <id>`, and omitting it continues from the previous task's end.
    `end` is a bare number (absolute); a duration carries a unit suffix
    (`5s`, `2d`; the unit itself is ignored).
    """
    parts = [p.strip() for p in spec.split(",")]
    parts = [p for p in parts if p not in ("done", "active", "crit", "milestone")]
    task_id = None
    if len(parts) > 1 and not NUM_RE.match(parts[0]) and not parts[0].startswith("after "):
        task_id = parts.pop(0)
    start = None
    if len(parts) == 2:
        s = parts.pop(0)
        start = ids.get(s.split(None, 1)[1].strip(), prev_end) if s.startswith("after ") else float(s)
    elif len(parts) != 1:
        raise ValueError(f"unsupported gantt task spec: {name!r}: {spec!r}")
    if start is None:
        start = prev_end
    end_spec = parts[0]
    end_num = float(re.match(r'-?\d+(?:\.\d+)?', end_spec).group(0))
    end = end_num if NUM_RE.match(end_spec) else start + end_num
    if task_id:
        ids[task_id] = end
    return name, start, end


def parse_gantt(text):
    title = None
    axis_format = "%S"
    sections = []  # [(name, [(task, start, end), ...])]
    ids = {}
    prev_end = 0.0
    for raw in text.splitlines():
        line = raw.split("%%", 1)[0].strip()
        if not line or line == "gantt":
            continue
        if line.startswith("title "):
            title = line[6:].strip()
        elif line.startswith("dateFormat"):
            continue
        elif line.startswith("axisFormat"):
            axis_format = line.split(None, 1)[1].strip()
        elif line.startswith("section "):
            sections.append((line[8:].strip(), []))
        elif line.startswith(("excludes", "todayMarker", "tickInterval", "weekday")):
            continue
        else:
            m = TASK_RE.match(line)
            if not m:
                continue
            if not sections:
                sections.append(("", []))
            task = _parse_task(m.group(1), m.group(2), prev_end, ids)
            prev_end = task[2]
            sections[-1][1].append(task)
    return title, axis_format, sections


def _tick_label(value, axis_format):
    if "%S" in axis_format or "%M" in axis_format or "%H" in axis_format:
        return f"{int(value):02d}"
    return f"{value:g}"


def _wrap(text, max_chars):
    words = []
    for w in text.split():  # hyphenate words too long for the column ("back-ground")
        while len(w) > max_chars:
            words.append(w[:max_chars - 1] + "-")
            w = w[max_chars - 1:]
        words.append(w)
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def _text(text, x, y, width, font_size, align, group_ids, family=GANTT_FONT_FAMILY,
          background="transparent"):
    lines = text.count("\n") + 1
    return _base(
        new_id(), "text", x, y, width, font_size * 1.25 * lines, group_ids,
        strokeColor=GANTT_TEXT, backgroundColor=background,
        text=text, originalText=text, fontSize=font_size, fontFamily=family,
        textAlign=align, verticalAlign="top", containerId=None,
        autoResize=False, lineHeight=1.25,
    )


def convert_gantt(mermaid_text):
    title, axis_format, sections = parse_gantt(mermaid_text)
    tasks = [t for _, ts in sections for t in ts]
    if not tasks:
        raise ValueError("gantt has no tasks")
    t_min = min(s for _, s, _ in tasks)
    t_max = max(e for _, _, e in tasks)
    n_units = max(1, int(t_max - t_min + 0.999))
    x0, y0 = 604.0, 1796.0
    band_x = x0 - GANTT_LABEL_COL_W
    band_w = GANTT_LABEL_COL_W + n_units * GANTT_UNIT_W + GANTT_UNIT_W - 12
    tx = lambda t: x0 + (t - t_min) * GANTT_UNIT_W

    bands, bars, side_labels, section_labels = [], [], [], []
    y = y0
    for idx, (name, ts) in enumerate(sections):
        bar_fill, tint = GANTT_PALETTE[idx % len(GANTT_PALETTE)]
        band_h = 2 * GANTT_BAND_PAD_Y + max(len(ts), 1) * GANTT_ROW_STRIDE
        bands.append(_base(new_id(), "rectangle", band_x, y, band_w, band_h, [],
                           backgroundColor=tint))
        if name:
            label = _wrap(name, 8)
            n_lines = label.count("\n") + 1
            lh = GANTT_SECTION_FONT * 1.25 * n_lines
            section_labels.append(_text(
                label, band_x + GANTT_LABEL_PAD_X, y + (band_h - lh) / 2,
                GANTT_LABEL_COL_W - 2 * GANTT_LABEL_PAD_X, GANTT_SECTION_FONT,
                "center", []))
        ry = y + GANTT_BAND_PAD_Y
        for task, start, end in ts:
            gid = [new_id()]
            bx, bw = tx(start), max(end - start, 0.05) * GANTT_UNIT_W
            bars.append(_base(new_id(), "rectangle", bx, ry, bw, GANTT_BAR_H, gid,
                              backgroundColor=bar_fill, strokeWidth=2,
                              roundness={"type": 3}))
            text_w = len(task) * GANTT_BAR_FONT * GANTT_CHAR_W
            if text_w + 16 <= bw:
                bars.append(_text(task, bx + (bw - text_w) / 2, ry + 4, text_w,
                                  GANTT_BAR_FONT, "center", gid,
                                  background=bar_fill))
            else:
                # left-aligned so the text hugs the bar regardless of how far
                # the width heuristic overshoots the real glyph widths
                sw = len(task) * GANTT_SIDE_FONT * GANTT_CHAR_W + 4
                sx, sy = bx + bw + GANTT_SIDE_GAP_X, ry + 5
                side_labels.append(_base(new_id(), "rectangle", sx - 2, sy, sw, 19, [],
                                         strokeColor="transparent",
                                         backgroundColor=tint))
                side_labels.append(_text(task, sx, sy + 1, sw, GANTT_SIDE_FONT,
                                         "left", gid))
            ry += GANTT_ROW_STRIDE
        y += band_h
    y_end = y

    grid, ticks = [], []
    for i in range(n_units + 1):
        gx = x0 + i * GANTT_UNIT_W
        grid.append(_base(new_id(), "line", gx, y0, 0, y_end - y0, [],
                          backgroundColor="#ffffff",
                          points=[[0, 0], [0, y_end - y0]],
                          startBinding=None, endBinding=None,
                          startArrowhead=None, endArrowhead=None,
                          lastCommittedPoint=None, elbowed=False))
        lbl = _tick_label(t_min + i, axis_format)
        tw = len(lbl) * GANTT_TICK_FONT * GANTT_CHAR_W
        ticks.append(_text(lbl, gx - tw / 2, y_end + GANTT_TICK_GAP_Y, tw,
                           GANTT_TICK_FONT, "center", []))

    title_els = []
    if title:
        tw = len(title) * GANTT_TITLE_FONT * 0.57
        pill_w = tw + 2 * GANTT_TITLE_PAD_X
        px = band_x + (band_w - pill_w) / 2
        py = y0 - GANTT_TITLE_GAP_Y - GANTT_TITLE_H
        title_els.append(_base(new_id(), "rectangle", px, py, pill_w, GANTT_TITLE_H, [],
                               strokeColor="transparent",
                               backgroundColor=GANTT_PALETTE[0][0],
                               roughness=2, roundness={"type": 3}))
        title_els.append(_text(title, px + GANTT_TITLE_PAD_X, py + 10, tw,
                               GANTT_TITLE_FONT, "center", [],
                               family=GANTT_TITLE_FONT_FAMILY))

    # draw order: bands, grid, bars (+ inside labels), side labels, ticks, sections, title
    return bands + grid + bars + side_labels + ticks + section_labels + title_els
