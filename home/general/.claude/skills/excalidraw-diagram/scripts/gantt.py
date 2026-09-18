"""mermaid `gantt` -> Excalidraw timeline.

Supported syntax (a subset of mermaid's, matching its semantics):

- `title`, `section`, `%%` comments, `dateFormat`, `axisFormat`, `excludes`,
  `includes`; `todayMarker`/`tickInterval`/`weekday` are ignored.
- Numeric axis when `dateFormat` is absent or numeric (`s`, `x`): task times
  are bare numbers and a duration's unit suffix is ignored (`5s` == 5).
- Date axis when `dateFormat` uses `YYYY`/`MM`/`DD` (plus `HH`/`mm`/`ss`):
  times are dates in that format and durations are `Nd`/`Nh`/`Nm`/`Nw`
  (hours are fractional days, so `20h` ~= 0.83 of a grid column).
- Task spec after the colon: `[tags,] [id,] [start,] end` with tags from
  `done`/`active`/`crit`/`milestone`, start as a literal or `after <id>...`
  (latest end of the listed ids), end as a literal, a duration or
  `until <id>` (that task's start; forward references resolve). An omitted
  start continues from the previous task's end (any section).
- `excludes weekends|<dayname>...|<date>...` compresses the axis: dates map
  to a working-day index, durations skip excluded days (a 5d task starting
  Friday ends the next Friday, as in mermaid) and only working days get a
  grid column. A literal date on an excluded day snaps to the next working
  day. `includes` re-admits days.
- Tag styling: `done` = grey fill/stroke, `active` = bolder stroke, `crit` =
  red fill/stroke (`crit,done` keeps the grey fill with a soft red stroke),
  `milestone` = a small diamond centred on its date with the label beside it.

Styling was reverse-engineered from a hand-converted reference gantt
(`example-gantt.excalidraw`): one tinted full-width band per section with
its wrapped title in a label column on the left, a vertical grid line per
axis unit spanning all bands, one row per task with a rounded solid bar
(width = duration * GANTT_UNIT_W), a bar label centred inside the bar or,
when the bar is too narrow, placed just to the right of it in a smaller
face over a band-tinted backing so it stays legible across grid lines, tick
labels under the bottom band (staggered onto two rows when they would
overlap) and a hand-drawn (roughness 2) title pill above.
"""
import math
import re
from datetime import date, datetime

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
GANTT_MILESTONE_SIZE = 21.0    # diamond side, centred in the row
GANTT_BORDER = "#1e1e1e"
GANTT_TEXT = "#1e1e1e"
GANTT_DONE_FILL = "#e9ecef"
GANTT_DONE_STROKE = "#868e96"
GANTT_CRIT_FILL = "#ffc9c9"
GANTT_CRIT_STROKE = "#e03131"
GANTT_CRIT_DONE_STROKE = "#ff8787"
GANTT_ACTIVE_STROKE_W = 3      # untagged bars use 2
GANTT_DEFAULT_AXIS_FORMAT = "%b %d"
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
DURATION_RE = re.compile(r'^(\d+(?:\.\d+)?)\s*([a-z]*)$')
TAGS = ("done", "active", "crit", "milestone")
DAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday",
             "saturday", "sunday")
# mermaid (moment/dayjs) dateFormat tokens -> strptime directives
DATE_TOKENS = (("YYYY", "%Y"), ("YY", "%y"), ("MM", "%m"), ("DD", "%d"),
               ("HH", "%H"), ("mm", "%M"), ("ss", "%S"))
DURATION_DAYS = {"d": 1.0, "h": 1 / 24, "m": 1 / 1440, "s": 1 / 86400,
                 "w": 7.0}


class Calendar:
    """Maps dates to fractional working-day indices and back.

    Index 0 is the earliest literal date in the diagram; each non-excluded
    day after it adds one. With nothing excluded this is a plain day count.
    """

    def __init__(self, origin, excluded_weekdays=(), excluded_dates=(),
                 include_dates=()):
        self.origin = origin  # date ordinal
        self.weekdays = set(excluded_weekdays)
        self.dates = set(excluded_dates)
        self.includes = set(include_dates)
        self._days = []       # ordinal of each working day, index order

    def excluded(self, ordinal):
        if ordinal in self.includes:
            return False
        return ordinal in self.dates or date.fromordinal(ordinal).weekday() in self.weekdays

    def _fill(self, upto_ordinal=None, upto_index=None):
        nxt = self._days[-1] + 1 if self._days else self.origin
        while (upto_ordinal is not None and nxt <= upto_ordinal) or (
                upto_index is not None and len(self._days) <= upto_index):
            if not self.excluded(nxt):
                self._days.append(nxt)
            nxt += 1

    def index(self, t):
        """Working-day index of a float time (ordinal + fraction of a day)."""
        ordinal = math.floor(t)
        self._fill(upto_ordinal=ordinal)
        idx = sum(1 for d in self._days if d < ordinal)
        return idx + (t - ordinal)

    def date_at(self, index):
        self._fill(upto_index=index)
        return date.fromordinal(self._days[index])


def _strptime_format(date_format):
    fmt = date_format
    for token, code in DATE_TOKENS:
        fmt = fmt.replace(token, code)
    return fmt


def _parse_date(text, strp_fmt):
    """Float ordinal (days, with time-of-day fraction) for a literal date."""
    for fmt in (strp_fmt, "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt)
        except ValueError:
            continue
        secs = dt.hour * 3600 + dt.minute * 60 + dt.second
        return dt.toordinal() + secs / 86400
    return None


def _split_spec(spec, is_start):
    """Split a task spec into (tags, id, start_spec, end_spec).

    Mermaid reads the untagged parts positionally: `end`, `start, end` or
    `id, start, end`. A two-part `id, end` (no start) is accepted too when
    the first part cannot be a start time.
    """
    parts = [p.strip() for p in spec.split(",")]
    tags = {p for p in parts if p in TAGS}
    parts = [p for p in parts if p not in TAGS]
    if len(parts) == 3:
        return tags, parts[0], parts[1], parts[2]
    if len(parts) == 2 and is_start(parts[0]):
        return tags, None, parts[0], parts[1]
    if len(parts) == 2:
        return tags, parts[0], None, parts[1]
    if len(parts) == 1:
        return tags, None, None, parts[0]
    raise ValueError(f"unsupported gantt task spec: {spec!r}")


def _parse_excludes(text, strp_fmt):
    """(weekdays, ordinals) named by an `excludes`/`includes` line."""
    weekdays, ordinals = set(), set()
    for tok in re.split(r'[\s,]+', text.strip().lower()):
        if tok == "weekends":
            weekdays.update((5, 6))
        elif tok in DAY_NAMES:
            weekdays.add(DAY_NAMES.index(tok))
        elif tok:
            d = _parse_date(tok, strp_fmt)
            if d is not None:
                ordinals.add(int(d))  # unknown tokens are ignored silently
    return weekdays, ordinals


def parse_gantt(text):
    """Return (title, axis_format, sections, calendar).

    `sections` is [(name, [(task, start, end, tags), ...])] with times as
    floats in axis units; `calendar` is None on a numeric axis.
    """
    title = None
    date_format, axis_format = None, None
    sections = []
    raw = []  # (section_idx, name, tags, id, start_spec, end_spec)
    excludes, includes = "", ""
    for line in text.splitlines():
        line = line.split("%%", 1)[0].strip()
        if not line or line == "gantt":
            continue
        if line.startswith("title "):
            title = line[6:].strip()
        elif line.startswith("dateFormat"):
            date_format = line.split(None, 1)[1].strip() if " " in line else None
        elif line.startswith("axisFormat"):
            axis_format = line.split(None, 1)[1].strip()
        elif line.startswith("section "):
            sections.append((line[8:].strip(), []))
        elif line.startswith("excludes"):
            excludes = line[8:]
        elif line.startswith("includes"):
            includes = line[8:]
        elif line.startswith(("todayMarker", "tickInterval", "weekday")):
            continue
        else:
            m = TASK_RE.match(line)
            if not m:
                continue
            if not sections:
                sections.append(("", []))
            raw.append((len(sections) - 1, m.group(1), m.group(2)))

    date_mode = bool(date_format) and any(t in date_format for t in ("YYYY", "MM", "DD"))
    strp_fmt = _strptime_format(date_format) if date_mode else None
    calendar = None
    if date_mode:
        literals = [_parse_date(p.strip(), strp_fmt)
                    for _, _, spec in raw for p in spec.split(",")]
        literals = [d for d in literals if d is not None]
        origin = int(min(literals)) if literals else date.today().toordinal()
        calendar = Calendar(origin, *_parse_excludes(excludes, strp_fmt),
                            include_dates=_parse_excludes(includes, strp_fmt)[1])
        if axis_format is None:
            axis_format = GANTT_DEFAULT_AXIS_FORMAT

    def to_time(text):
        """Literal start/end -> axis units, or None if it is not a literal."""
        if not date_mode:
            return float(text) if NUM_RE.match(text) else None
        d = _parse_date(text, strp_fmt)
        return None if d is None else calendar.index(d)

    def is_start(text):
        return text.startswith("after ") or to_time(text) is not None

    specs = [(sec, name) + _split_spec(spec, is_start) for sec, name, spec in raw]
    times = _resolve(specs, to_time, date_mode)
    for (sec, name, tags, _, _, _), (start, end) in zip(specs, times):
        sections[sec][1].append((name, start, end, tags))
    return title, axis_format or "%S", sections, calendar


def _resolve(specs, to_time, date_mode):
    """Turn (section, name, tags, id, start_spec, end_spec) rows into times.

    Passes over the list until every task resolves, so `until`/`after` may
    point at tasks defined later; an omitted start is the previous task's
    end (which therefore has to resolve first).
    """
    times = [None] * len(specs)
    ids = {}
    progress = True
    while progress and None in times:
        progress = False
        for i, (_, name, tags, task_id, start_spec, end_spec) in enumerate(specs):
            if times[i] is not None:
                continue
            start = _resolve_start(start_spec, i, times, ids, to_time)
            if start is None:
                continue
            end = _resolve_end(end_spec, start, ids, to_time, date_mode)
            if end is None:
                continue
            if "milestone" in tags:
                end = start
            times[i] = (start, end)
            if task_id:
                ids[task_id] = times[i]
            progress = True
    unresolved = [specs[i][1] for i, t in enumerate(times) if t is None]
    if unresolved:
        raise ValueError(f"gantt tasks with unknown start/end references: {unresolved}")
    return times


def _resolve_start(spec, i, times, ids, to_time):
    if spec is None:
        if i == 0:
            return 0.0
        return times[i - 1][1] if times[i - 1] else None
    if spec.startswith("after "):
        deps = [ids.get(d) for d in spec[6:].split()]
        return None if None in deps else max(t[1] for t in deps)
    t = to_time(spec)
    if t is None:
        raise ValueError(f"unsupported gantt start time: {spec!r}")
    return t


def _resolve_end(spec, start, ids, to_time, date_mode):
    if spec.startswith("until "):
        dep = ids.get(spec[6:].strip())
        return None if dep is None else dep[0]
    m = DURATION_RE.match(spec)
    if m and (m.group(2) or not date_mode):
        n, unit = float(m.group(1)), m.group(2)
        if not unit:
            return n  # bare number on a numeric axis is an absolute end
        return start + n * (DURATION_DAYS.get(unit, 1.0) if date_mode else 1.0)
    t = to_time(spec)
    if t is None:
        raise ValueError(f"unsupported gantt end time: {spec!r}")
    return t


def _tick_label(value, axis_format, calendar):
    if calendar is not None:
        return calendar.date_at(int(value)).strftime(axis_format)
    if "%S" in axis_format or "%M" in axis_format or "%H" in axis_format:
        return f"{int(value):02d}"
    return f"{value:g}"


def _bar_style(tags, bar_fill):
    """(fill, stroke, stroke width) for a task's tags, mermaid-style."""
    fill, stroke, width = bar_fill, GANTT_BORDER, 2
    if "crit" in tags:
        fill, stroke = GANTT_CRIT_FILL, GANTT_CRIT_STROKE
    if "done" in tags:
        fill = GANTT_DONE_FILL
        stroke = GANTT_CRIT_DONE_STROKE if "crit" in tags else GANTT_DONE_STROKE
    if "active" in tags:
        width = GANTT_ACTIVE_STROKE_W
    return fill, stroke, width


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


def _side_label_w(task):
    return len(task) * GANTT_SIDE_FONT * GANTT_CHAR_W + 4


def _bar_geometry(start, end, tags, tx):
    """(x, width, label fits inside) for a task bar or milestone."""
    if "milestone" in tags:
        return tx(start) - GANTT_MILESTONE_SIZE / 2, GANTT_MILESTONE_SIZE, False
    return tx(start), max(end - start, 0.05) * GANTT_UNIT_W, True


def convert_gantt(mermaid_text):
    title, axis_format, sections, calendar = parse_gantt(mermaid_text)
    tasks = [t for _, ts in sections for t in ts]
    if not tasks:
        raise ValueError("gantt has no tasks")
    t_min = math.floor(min(s for _, s, _, _ in tasks))
    t_max = max(e for _, _, e, _ in tasks)
    n_units = max(1, int(t_max - t_min + 0.999))
    x0, y0 = 604.0, 1796.0
    band_x = x0 - GANTT_LABEL_COL_W
    band_w = GANTT_LABEL_COL_W + n_units * GANTT_UNIT_W + GANTT_UNIT_W - 12
    tx = lambda t: x0 + (t - t_min) * GANTT_UNIT_W

    # widen the bands if a side label would otherwise run past the right edge
    for task, start, end, tags in tasks:
        bx, bw, can_fit = _bar_geometry(start, end, tags, tx)
        if can_fit and len(task) * GANTT_BAR_FONT * GANTT_CHAR_W + 16 <= bw:
            continue
        right = bx + bw + GANTT_SIDE_GAP_X + _side_label_w(task) + 12
        band_w = max(band_w, right - band_x)

    bands, bars, side_labels, section_labels = [], [], [], []
    y = y0
    for idx, (name, ts) in enumerate(sections):
        section_fill, tint = GANTT_PALETTE[idx % len(GANTT_PALETTE)]
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
        for task, start, end, tags in ts:
            gid = [new_id()]
            fill, stroke, stroke_w = _bar_style(tags, section_fill)
            bx, bw, can_fit = _bar_geometry(start, end, tags, tx)
            if "milestone" in tags:
                by = ry + (GANTT_BAR_H - GANTT_MILESTONE_SIZE) / 2
                bars.append(_base(new_id(), "diamond", bx, by, bw, bw, gid,
                                  backgroundColor=fill, strokeColor=stroke,
                                  strokeWidth=stroke_w))
            else:
                bars.append(_base(new_id(), "rectangle", bx, ry, bw, GANTT_BAR_H, gid,
                                  backgroundColor=fill, strokeColor=stroke,
                                  strokeWidth=stroke_w, roundness={"type": 3}))
            text_w = len(task) * GANTT_BAR_FONT * GANTT_CHAR_W
            if can_fit and text_w + 16 <= bw:
                bars.append(_text(task, bx + (bw - text_w) / 2, ry + 4, text_w,
                                  GANTT_BAR_FONT, "center", gid,
                                  background=fill))
            else:
                # left-aligned so the text hugs the bar regardless of how far
                # the width heuristic overshoots the real glyph widths
                sw = _side_label_w(task)
                sx, sy = bx + bw + GANTT_SIDE_GAP_X, ry + 5
                side_labels.append(_base(new_id(), "rectangle", sx - 2, sy, sw, 19, [],
                                         strokeColor="transparent",
                                         backgroundColor=tint))
                side_labels.append(_text(task, sx, sy + 1, sw, GANTT_SIDE_FONT,
                                         "left", gid))
            ry += GANTT_ROW_STRIDE
        y += band_h
    y_end = y

    labels = [_tick_label(t_min + i, axis_format, calendar) for i in range(n_units + 1)]
    widths = [len(lbl) * GANTT_TICK_FONT * GANTT_CHAR_W for lbl in labels]
    stagger = max(widths) + 8 > GANTT_UNIT_W  # alternate rows when labels would touch
    grid, ticks = [], []
    for i, (lbl, tw) in enumerate(zip(labels, widths)):
        gx = x0 + i * GANTT_UNIT_W
        grid.append(_base(new_id(), "line", gx, y0, 0, y_end - y0, [],
                          backgroundColor="#ffffff",
                          points=[[0, 0], [0, y_end - y0]],
                          startBinding=None, endBinding=None,
                          startArrowhead=None, endArrowhead=None,
                          lastCommittedPoint=None, elbowed=False))
        ty = y_end + GANTT_TICK_GAP_Y
        if stagger and i % 2:
            ty += GANTT_TICK_FONT * 1.25
        ticks.append(_text(lbl, gx - tw / 2, ty, tw, GANTT_TICK_FONT, "center", []))

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
