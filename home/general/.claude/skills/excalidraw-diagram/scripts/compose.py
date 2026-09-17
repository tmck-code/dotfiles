#!/usr/bin/env python3
'''Compose several mermaid sub-diagrams into one Excalidraw scene.

Each panel's mermaid source is converted with `convert.py`, dropped into a
white rounded panel, and the panels are joined by hand-drawn "chrome" that
reproduces the look of Excalidraw's own use-case examples scene: a wavy
spine line, a heading and footer box at its ends, a junction dot per panel,
a coloured branch line through a category label box, a same-colour backing
card offset under each panel, and (optionally) a pale wash blob behind it.

Usage: compose.py <scene.toml> <output.excalidraw> [--seed N]

Scene TOML keys (all optional except `panels`):

    layout        = 'river' | 'grid' | 'row'      (default 'river')
    title         = 'Heading text'                (omit for no heading)
    footer        = 'Footer text'                 (omit for no footer)
    seed          = 1                             (wobble RNG seed)
    sloppiness    = 1 | 2 | 3                     (chrome roughness, default 2)
    shadow        = 'colour' | 'grey' | 'none'    (default 'colour')
    blobs         = true | false                  (default true)
    double_stroke = true | false                  (default true)
    labels        = 'branch' | 'tab' | 'none'     (default 'branch')
    columns       = 2                             (grid: max slots per band)
    connectors    = true | false                  (grid: S-curves panel i -> i+1)

    [[panels]]
    label      = 'Flowchart'
    file       = 'example-flowchart.mmd'  # relative to the toml file
    scale      = 0.7                      # convert(scale=)
    sloppiness = 1                        # convert(sloppiness=)
    corners    = 'round'                  # convert(corners=), optional
    colour     = '#ff8787'                # optional, else palette cycle
'''

from __future__ import annotations

import json
import math
import os
import random
import sys
import textwrap
import tomllib

from convert import convert, finalise, new_id

PALETTE = ['#ff8787', '#d2bab0', '#da77f2', '#ffa94d', '#38d9a9', '#ffd43b', '#4dabf7']
TINTS   = ['#fff5f5', '#f8f0fc', '#f3f0ff', '#fff4e6', '#e6fcf5', '#fff9db', '#e7f5ff']
SPINE_COLOUR = '#6965db'
INK          = '#1e1e1e'
DOT_INK      = '#000000'
WHITE        = '#ffffff'
GREY_SHADOW  = '#ced4da'
TRANSPARENT  = 'transparent'

SLOPPINESS_ROUGHNESS = {1: 0, 2: 1, 3: 2}
SHADOW_MODES = ('colour', 'grey', 'none')
LABEL_MODES  = ('branch', 'tab', 'none')
LAYOUTS      = ('river', 'grid', 'row')

PANEL_PAD     = 60.0
NEAR_EDGE     = 350.0     # panel near edge from the spine centre-line
SAME_SIDE_GAP = 200.0     # min vertical gap between panels on one side
WALK_GAP      = 300.0     # y walk: prev height * WALK_FRACTION + WALK_GAP
WALK_FRACTION = 0.55
GRID_GAP      = 260.0
TALL_RATIO    = 2.0       # grid: left neighbour this much taller -> stack beside it
CONNECTOR_AMP = 20.0      # grid connector wobble
BRANCH_INSET  = 15.0      # branch end past the panel's near edge
LABEL_ALONG   = 170.0     # label box centre distance from the junction dot
SPINE_STEP    = 100.0
SPINE_AMP     = 60.0
BRANCH_AMP    = 40.0

LABEL_W, LABEL_H       = 170.22, 68.56
LABEL_BACK_W, LABEL_BACK_H = 170.07, 70.48
LABEL_BACK_DX, LABEL_BACK_DY = 5.0, 4.0
LABEL_FONT             = 23.66
LABEL_PAD_X            = 40.0
HEADING_W, HEADING_H   = 285.04, 115.0
HEADING_BACK_DX, HEADING_BACK_DY = 6.6, 8.0
HEADING_WRAP           = 22
HEADING_GAP            = 70.0     # heading centre to spine start
DOT_SIZE               = 28.24
DOT_BACK_DX, DOT_BACK_DY = 4.0, 3.4
SHADOW_DX, SHADOW_DY   = 8.0, 10.0
INK_LINE_DX, INK_LINE_DY = -2.0, -5.0
BLOB_MARGIN_X, BLOB_MARGIN_Y = 220.0, 180.0
BLOB_POINTS            = 30
BLOB_PULL              = 150.0    # blob centre pulled toward the spine
CHAR_W                 = 0.55
LINE_H                 = 1.25

USAGE = 'usage: compose.py <scene.toml> <output.excalidraw> [--seed N]'


class Panel:
    def __init__(self, label, elements, colour, tint):
        self.label = label
        self.elements = elements
        self.colour = colour
        self.tint = tint
        x0, y0, x1, y1 = bbox(elements)
        self.content_dx = -x0
        self.content_dy = -y0
        self.w = (x1 - x0) + 2 * PANEL_PAD
        self.h = (y1 - y0) + 2 * PANEL_PAD
        self.x = 0.0
        self.y = 0.0
        # filled by the layout
        self.dot = None        # junction (cx, cy) or None
        self.branch = []       # absolute points from the dot to the panel
        self.label_centre = None
        self.blob_centre = None

    @property
    def centre(self):
        return (self.x + self.w / 2, self.y + self.h / 2)

    def place_content(self):
        dx = self.x + PANEL_PAD + self.content_dx
        dy = self.y + PANEL_PAD + self.content_dy
        for el in self.elements:
            el['x'] += dx
            el['y'] += dy
        return self.elements


def bbox(elements):
    'Bounding box (x0, y0, x1, y1) over shapes, text and line points.'
    xs, ys = [], []
    for el in elements:
        points = el.get('points') or [[0, 0], [el['width'], el['height']]]
        for px, py in points:
            xs.append(el['x'] + px)
            ys.append(el['y'] + py)
    return min(xs), min(ys), max(xs), max(ys)


class Chrome:
    'Builds chrome elements with the scene-level style switches applied.'

    def __init__(self, scene, rng):
        self.rng = rng
        self.roughness = SLOPPINESS_ROUGHNESS[scene.get('sloppiness', 2)]
        self.shadow = scene.get('shadow', 'colour')
        self.blobs = scene.get('blobs', True)
        self.double_stroke = scene.get('double_stroke', True)
        self.labels = scene.get('labels', 'branch')
        self.check(scene)

    def check(self, scene):
        if scene.get('sloppiness', 2) not in SLOPPINESS_ROUGHNESS:
            raise ValueError('sloppiness must be 1, 2 or 3')
        if self.shadow not in SHADOW_MODES:
            raise ValueError(f'shadow must be one of {SHADOW_MODES}')
        if self.labels not in LABEL_MODES:
            raise ValueError(f'labels must be one of {LABEL_MODES}')

    def base(self, el_type, x, y, width, height, **extra):
        el = {
            'id'              : new_id(),
            'type'            : el_type,
            'x'               : x,
            'y'               : y,
            'width'           : width,
            'height'          : height,
            'angle'           : 0,
            'strokeColor'     : INK,
            'backgroundColor' : TRANSPARENT,
            'fillStyle'       : 'solid',
            'strokeWidth'     : 2,
            'strokeStyle'     : 'solid',
            'roughness'       : self.roughness,
            'opacity'         : 100,
            'groupIds'        : [],
            'frameId'         : None,
            'roundness'       : None,
            'seed'            : self.rng.randrange(1, 2**31),
            'version'         : 1,
            'versionNonce'    : self.rng.randrange(1, 2**31),
            'isDeleted'       : False,
            'boundElements'   : [],
            'updated'         : 1,
            'link'            : None,
            'locked'          : False,
        }
        el.update(extra)
        return el

    def rect(self, x, y, w, h, stroke, bg, sw=2):
        return self.base(
            'rectangle', x, y, w, h,
            strokeColor     = stroke,
            backgroundColor = bg,
            strokeWidth     = sw,
            roundness       = {'type': 3},
        )

    def ellipse(self, cx, cy, size, stroke, bg, sw=2):
        return self.base(
            'ellipse', cx - size / 2, cy - size / 2, size, size,
            strokeColor     = stroke,
            backgroundColor = bg,
            strokeWidth     = sw,
            roundness       = {'type': 2},
        )

    def line(self, abs_points, stroke, sw, dx=0.0, dy=0.0, **extra):
        x0, y0 = abs_points[0]
        rel = [[px - x0, py - y0] for px, py in abs_points]
        xs = [p[0] for p in rel]
        ys = [p[1] for p in rel]
        fields = {
            'strokeColor'        : stroke,
            'backgroundColor'    : stroke,
            'strokeWidth'        : sw,
            'roundness'          : {'type': 2},
            'points'             : rel,
            'startBinding'       : None,
            'endBinding'         : None,
            'lastCommittedPoint' : None,
            'startArrowhead'     : None,
            'endArrowhead'       : None,
            'polygon'            : False,
        }
        fields.update(extra)
        return self.base(
            'line', x0 + dx, y0 + dy, max(xs) - min(xs), max(ys) - min(ys), **fields)

    def text(self, container, lines, font_size, colour=INK):
        joined = '\n'.join(lines)
        tw = max(len(line) for line in lines) * font_size * CHAR_W
        th = font_size * LINE_H * len(lines)
        el = self.base(
            'text',
            container['x'] + (container['width'] - tw) / 2,
            container['y'] + (container['height'] - th) / 2,
            tw, th,
            strokeColor   = colour,
            text          = joined,
            originalText  = joined,
            fontSize      = font_size,
            fontFamily    = 1,
            textAlign     = 'center',
            verticalAlign = 'middle',
            containerId   = container['id'],
            autoResize    = True,
            lineHeight    = LINE_H,
        )
        container['boundElements'] = [{'id': el['id'], 'type': 'text'}]
        return el

    def shadow_colour(self, colour):
        if self.shadow == 'grey':
            return GREY_SHADOW
        return colour

    def double_line(self, points, colour, sw_colour=4):
        'Return (under, over): the colour copy and the ink copy of a line.'
        if not self.double_stroke:
            return [], [self.line(points, INK, 2)]
        under = self.line(points, colour, sw_colour)
        over = self.line(points, INK, 2, INK_LINE_DX, INK_LINE_DY,
                         backgroundColor=colour)
        return [under], [over]

    def label_box(self, cx, cy, label, colour, w=LABEL_W, h=LABEL_H,
                  font_size=LABEL_FONT, back_sw=2, back_dx=LABEL_BACK_DX,
                  back_dy=LABEL_BACK_DY, wrap=None):
        'Return (under, over): backing card, then white box + bound text.'
        lines = textwrap.wrap(label, wrap) if wrap else [label]
        tw = max(len(line) for line in lines) * font_size * CHAR_W
        th = font_size * LINE_H * len(lines)
        w = max(w, tw + LABEL_PAD_X)
        h = max(h, th + LABEL_PAD_X)
        x, y = cx - w / 2, cy - h / 2
        under = []
        if self.shadow != 'none':
            under.append(self.rect(
                x + back_dx, y + back_dy, w - 0.15, h + 1.92,
                TRANSPARENT, self.shadow_colour(colour), back_sw))
        box = self.rect(x, y, w, h, INK, WHITE)
        return under, [box, self.text(box, lines, font_size)]

    def dot(self, cx, cy, colour):
        under = []
        if self.shadow != 'none':
            under.append(self.ellipse(
                cx + DOT_BACK_DX, cy + DOT_BACK_DY, DOT_SIZE,
                TRANSPARENT, self.shadow_colour(colour)))
        return under, [self.ellipse(cx, cy, DOT_SIZE, DOT_INK, WHITE)]

    def blob(self, cx, cy, rx, ry, colour, fill='hachure', opacity=100):
        pts = []
        for i in range(BLOB_POINTS):
            a = 2 * math.pi * i / BLOB_POINTS
            r = self.rng.uniform(0.86, 1.08)
            pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
        pts.append(pts[0])
        return self.line(
            pts, colour, 2,
            fillStyle = fill,
            opacity   = opacity,
            polygon   = True,
        )

    def panel_shadow(self, panel):
        if self.shadow == 'none':
            return []
        return [self.rect(
            panel.x + SHADOW_DX, panel.y + SHADOW_DY, panel.w, panel.h,
            TRANSPARENT, self.shadow_colour(panel.colour), 4)]

    def panel_rect(self, panel):
        return self.rect(panel.x, panel.y, panel.w, panel.h, INK, WHITE)


def wavy(rng, start, end, n, amp):
    'Points from start to end with a gentle S-curve wobble across the line.'
    (x0, y0), (x1, y1) = start, end
    length = math.hypot(x1 - x0, y1 - y0) or 1.0
    nx, ny = -(y1 - y0) / length, (x1 - x0) / length
    phase = rng.uniform(0, 2 * math.pi)
    scale = rng.uniform(0.6, 1.0)
    pts = []
    for i in range(n):
        t = i / (n - 1)
        wobble = amp * scale * math.sin(2 * math.pi * t + phase) * math.sin(math.pi * t)
        pts.append((x0 + (x1 - x0) * t + nx * wobble, y0 + (y1 - y0) * t + ny * wobble))
    return pts


def branch_points(rng, dot, end):
    n = rng.randint(7, 12)
    return wavy(rng, dot, end, n, BRANCH_AMP)


def point_along(points, distance):
    'The point `distance` px along a polyline from its first point.'
    run = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        if run + seg >= distance:
            t = (distance - run) / seg
            return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
        run += seg
    return points[-1]


class Meander:
    'Smooth deterministic wobble across a spine, evaluable at any position.'

    def __init__(self, rng):
        self.p1 = rng.uniform(0, 2 * math.pi)
        self.p2 = rng.uniform(0, 2 * math.pi)

    def at(self, t):
        return SPINE_AMP * (0.65 * math.sin(t / 320 + self.p1)
                            + 0.35 * math.sin(t / 150 + self.p2))


def layout_river(panels, rng, has_title, has_footer):
    'Vertical spine at x ~ 0; panels alternate right/left. Returns spine pts.'
    meander = Meander(rng)
    y = HEADING_GAP + 120 if has_title else 0.0
    walk = y
    side_bottom = {1: -1e9, -1: -1e9}
    for i, p in enumerate(panels):
        side = 1 if i % 2 == 0 else -1
        p.y = max(walk, side_bottom[side] + SAME_SIDE_GAP)
        cy = p.y + p.h / 2
        sx = meander.at(cy)
        p.x = sx + NEAR_EDGE if side > 0 else sx - NEAR_EDGE - p.w
        p.dot = (sx, cy)
        near_x = p.x + BRANCH_INSET if side > 0 else p.x + p.w - BRANCH_INSET
        p.branch = branch_points(rng, p.dot, (near_x, cy))
        p.label_centre = point_along(p.branch, LABEL_ALONG)
        p.blob_centre = (p.centre[0] - side * BLOB_PULL, cy)
        side_bottom[side] = p.y + p.h
        walk = p.y + p.h * WALK_FRACTION + WALK_GAP
    bottom = max(p.y + p.h for p in panels)
    end = bottom + (HEADING_GAP + 60 if has_footer else 0.0)
    ys = sorted({*frange(0.0, end, SPINE_STEP), end, *(p.dot[1] for p in panels)})
    return [(meander.at(t), t) for t in ys]


def layout_row(panels, rng, has_title, has_footer):
    'Horizontal spine at y ~ 0; panels alternate below/above.'
    meander = Meander(rng)
    x = HEADING_W / 2 + HEADING_GAP + 120 if has_title else 0.0
    walk = x
    side_right = {1: -1e9, -1: -1e9}
    for i, p in enumerate(panels):
        side = 1 if i % 2 == 0 else -1
        p.x = max(walk, side_right[side] + SAME_SIDE_GAP)
        cx = p.x + p.w / 2
        sy = meander.at(cx)
        p.y = sy + NEAR_EDGE if side > 0 else sy - NEAR_EDGE - p.h
        p.dot = (cx, sy)
        near_y = p.y + BRANCH_INSET if side > 0 else p.y + p.h - BRANCH_INSET
        p.branch = branch_points(rng, p.dot, (cx, near_y))
        p.label_centre = point_along(p.branch, LABEL_ALONG)
        p.blob_centre = (cx, p.centre[1] - side * BLOB_PULL)
        side_right[side] = p.x + p.w
        walk = p.x + p.w * WALK_FRACTION + WALK_GAP
    right = max(p.x + p.w for p in panels)
    end = right + (HEADING_W / 2 + HEADING_GAP + 60 if has_footer else 0.0)
    xs = sorted({*frange(0.0, end, SPINE_STEP), end, *(p.dot[0] for p in panels)})
    return [(t, meander.at(t)) for t in xs]


def layout_grid(panels, columns):
    '''Greedy packing: each panel goes in the free slot nearest the previous
    one, preferring its right edge, wrapping below once a band holds
    `columns` slots. A panel much shorter than its left neighbour (by
    TALL_RATIO) starts a vertical stack in that slot: following panels join
    the stack while it fits within the tall neighbour's height, and the
    stack is centred on that neighbour.'''
    band_y, band_right, slots = 0.0, 0.0, 0
    i = 0
    while i < len(panels):
        if slots == columns:
            band_y = max(p.y + p.h for p in panels[:i]) + GRID_GAP
            band_right, slots = 0.0, 0
        x = band_right + GRID_GAP if slots else 0.0
        left = panels[i - 1] if slots else None
        stack = grid_stack(panels, i, left)
        y = band_y
        if is_tall(left, panels[i]):
            y = left.y + (left.h - stack_height(stack)) / 2
        for p in stack:
            p.x, p.y = x, y
            p.label_centre = (p.x + 110, p.y)
            p.blob_centre = p.centre
            y += p.h + GRID_GAP
        band_right = max(p.x + p.w for p in stack)
        slots += 1
        i += len(stack)


def grid_stack(panels, i, left):
    '''Panels from `i` that stack vertically beside `left` (a panel much
    taller than panels[i]); just [panels[i]] otherwise.'''
    stack = [panels[i]]
    if not is_tall(left, panels[i]):
        return stack
    for p in panels[i + 1:]:
        if stack_height(stack + [p]) > left.h:
            break
        stack.append(p)
    return stack


def is_tall(left, panel):
    return left is not None and left.h > TALL_RATIO * panel.h


def stack_height(stack):
    return sum(p.h for p in stack) + GRID_GAP * (len(stack) - 1)


def frange(start, stop, step):
    n = int((stop - start) / step)
    return [start + i * step for i in range(n + 1)]


def grid_connectors(panels, rng):
    '''Sequential (panel, points): an S-curve between the pair of facing
    edges with the shortest gap, leaving and arriving perpendicular to them.'''
    for a, b in zip(panels, panels[1:]):
        yield a, s_curve(rng, *facing_edges(a, b))


def facing_edges(a, b):
    '''(start, end, axis): the closest facing edge pair between a and b.
    axis is 0 when the curve runs along x (right->left), 1 along y.'''
    gaps = {
        (0, +1): b.x - (a.x + a.w),
        (0, -1): a.x - (b.x + b.w),
        (1, +1): b.y - (a.y + a.h),
        (1, -1): a.y - (b.y + b.h),
    }
    open_gaps = {k: v for k, v in gaps.items() if v > 0} or gaps
    axis, sign = min(open_gaps, key=open_gaps.get)
    if axis == 0:
        a_lo, a_hi, b_lo, b_hi = a.y, a.y + a.h, b.y, b.y + b.h
    else:
        a_lo, a_hi, b_lo, b_hi = a.x, a.x + a.w, b.x, b.x + b.w
    a_mid, b_mid = (a_lo + a_hi) / 2, (b_lo + b_hi) / 2
    overlap_lo, overlap_hi = max(a_lo, b_lo), min(a_hi, b_hi)
    pull = (overlap_lo + overlap_hi) / 2 if overlap_lo < overlap_hi else (a_mid + b_mid) / 2
    leave, arrive = (a_mid + pull) / 2, (b_mid + pull) / 2
    if axis == 0:
        start = (a.x + a.w if sign > 0 else a.x, leave)
        end = (b.x if sign > 0 else b.x + b.w, arrive)
    else:
        start = (leave, a.y + a.h if sign > 0 else a.y)
        end = (arrive, b.y if sign > 0 else b.y + b.h)
    return start, end, axis


def s_curve(rng, start, end, axis, n=None):
    '''Points from start to end: linear along `axis`, smoothstep across it
    (perpendicular at both ends), plus a mild sine wobble.'''
    n = n or rng.randint(4, 6)
    amp = CONNECTOR_AMP * rng.uniform(0.5, 1.0)
    phase = rng.uniform(0, 2 * math.pi)
    along0, across0 = start[axis], start[1 - axis]
    along1, across1 = end[axis], end[1 - axis]
    pts = []
    for i in range(n):
        t = i / (n - 1)
        ease = t * t * (3 - 2 * t)
        wobble = amp * math.sin(2 * math.pi * t + phase) * math.sin(math.pi * t)
        along = along0 + (along1 - along0) * t
        across = across0 + (across1 - across0) * ease + wobble
        pts.append((along, across) if axis == 0 else (across, along))
    return pts


def heading_geometry(spine, at_start, layout):
    'Centre of a heading/footer box sitting off the spine start or end.'
    x, y = spine[0] if at_start else spine[-1]
    sign = -1 if at_start else 1
    if layout == 'row':
        return (x + sign * (HEADING_W / 2 + HEADING_GAP / 2), y)
    return (x, y + sign * HEADING_GAP)


def build_heading(chrome, centre, text, dot_at):
    under, over = [], []
    if chrome.blobs:
        under.append(chrome.blob(
            centre[0], centre[1], HEADING_W * 0.8, HEADING_H * 1.4,
            SPINE_COLOUR, opacity=20))
    box_under, box_over = chrome.label_box(
        centre[0], centre[1], text, SPINE_COLOUR,
        w       = HEADING_W,
        h       = HEADING_H,
        back_sw = 4,
        back_dx = HEADING_BACK_DX,
        back_dy = HEADING_BACK_DY,
        wrap    = HEADING_WRAP,
    )
    under += box_under
    over += box_over
    over.append(chrome.ellipse(dot_at[0], dot_at[1], DOT_SIZE, SPINE_COLOUR, WHITE, 4))
    return under, over


def compose_spine(scene, panels, chrome, rng):
    'River/row: spine + branches + dots + labels. Returns (under, over).'
    layout = scene['layout']
    title, footer = scene.get('title'), scene.get('footer')
    place = layout_river if layout == 'river' else layout_row
    spine = place(panels, rng, bool(title), bool(footer))
    z = {k: [] for k in ('blob', 'colour', 'back', 'shadow', 'ink', 'top')}
    for p in panels:
        if chrome.blobs:
            z['blob'].append(chrome.blob(
                *p.blob_centre, p.w / 2 + BLOB_MARGIN_X, p.h / 2 + BLOB_MARGIN_Y, p.tint))
        under, over = chrome.double_line(p.branch, p.colour)
        z['colour'] += under
        z['ink'] += over
        add_label(chrome, p, z)
        d_under, d_over = chrome.dot(*p.dot, p.colour)
        z['back'] += d_under
        z['top'] += d_over
        z['shadow'] += chrome.panel_shadow(p)
        z['top'].append(chrome.panel_rect(p))
    s_under, s_over = chrome.double_line(spine, SPINE_COLOUR)
    z['colour'] = s_under + z['colour']
    z['ink'] = s_over + z['ink']
    for text, at_start in ((title, True), (footer, False)):
        if not text:
            continue
        centre = heading_geometry(spine, at_start, layout)
        h_under, h_over = build_heading(chrome, centre, text, spine[0] if at_start else spine[-1])
        z['blob'] += h_under
        z['top'] += h_over
    return z['blob'] + z['colour'] + z['back'] + z['shadow'] + z['ink'], z['top']


def add_label(chrome, panel, z):
    if chrome.labels == 'none':
        return
    centre = panel.label_centre
    if chrome.labels == 'tab':
        centre = (panel.x + 110, panel.y)
    under, over = chrome.label_box(centre[0], centre[1], panel.label, panel.colour)
    z['back'] += under
    z['top'] += over


def compose_grid(scene, panels, chrome, rng):
    columns = scene.get('columns', 2)
    layout_grid(panels, columns)
    z = {k: [] for k in ('blob', 'colour', 'back', 'shadow', 'ink', 'top')}
    if scene.get('connectors', False):
        for p, points in grid_connectors(panels, rng):
            under, over = chrome.double_line(points, p.colour)
            z['colour'] += under
            z['ink'] += over
    for p in panels:
        if chrome.blobs:
            z['blob'].append(chrome.blob(
                *p.blob_centre, p.w / 2 + BLOB_MARGIN_X, p.h / 2 + BLOB_MARGIN_Y, p.tint))
        z['shadow'] += chrome.panel_shadow(p)
        z['top'].append(chrome.panel_rect(p))
    for p in panels:
        add_label(chrome, p, z)
    return z['blob'] + z['colour'] + z['back'] + z['shadow'] + z['ink'], z['top']


def load_panels(scene, toml_path):
    base = os.path.dirname(os.path.abspath(toml_path))
    for i, spec in enumerate(scene['panels']):
        with open(os.path.join(base, spec['file'])) as f:
            text = f.read()
        doc = convert(
            text,
            sloppiness = spec.get('sloppiness', 1),
            corners    = spec.get('corners'),
            scale      = spec.get('scale', 0.7),
        )
        colour = spec.get('colour', PALETTE[i % len(PALETTE)])
        tint = TINTS[PALETTE.index(colour)] if colour in PALETTE else TINTS[i % len(TINTS)]
        yield Panel(spec.get('label', spec['file']), doc['elements'], colour, tint)


def compose(scene, toml_path, seed=None):
    layout = scene.get('layout', 'river')
    if layout not in LAYOUTS:
        raise ValueError(f'layout must be one of {LAYOUTS}')
    scene['layout'] = layout
    rng = random.Random(seed if seed is not None else scene.get('seed', 1))
    chrome = Chrome(scene, rng)
    panels = list(load_panels(scene, toml_path))
    builder = compose_grid if layout == 'grid' else compose_spine
    under, over = builder(scene, panels, chrome, rng)
    content = [el for p in panels for el in p.place_content()]
    for p in panels:
        print(f'{p.label}: {p.w:.0f}x{p.h:.0f}, {len(p.elements)} elements', file=sys.stderr)
    elements = finalise(under + over + content)
    check_bindings(elements)
    return {
        'type'     : 'excalidraw',
        'version'  : 2,
        'source'   : 'https://app.excalidraw.com',
        'elements' : elements,
        'appState' : {'gridSize': None, 'viewBackgroundColor': WHITE},
        'files'    : {},
    }


def check_bindings(elements):
    ids = {el['id'] for el in elements}
    if len(ids) != len(elements):
        raise ValueError('duplicate element ids')
    for el in elements:
        for key in ('startBinding', 'endBinding'):
            binding = el.get(key)
            if binding and binding['elementId'] not in ids:
                raise ValueError(f'{el["id"]} {key} -> missing {binding["elementId"]}')
        if el.get('containerId') and el['containerId'] not in ids:
            raise ValueError(f'{el["id"]} containerId -> missing {el["containerId"]}')


def main():
    args = sys.argv[1:]
    seed = None
    if '--seed' in args:
        i = args.index('--seed')
        try:
            seed = int(args[i + 1])
        except (IndexError, ValueError):
            print(USAGE, file=sys.stderr)
            sys.exit(1)
        del args[i:i + 2]
    if len(args) != 2:
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    with open(args[0], 'rb') as f:
        scene = tomllib.load(f)
    doc = compose(scene, args[0], seed)
    with open(args[1], 'w') as f:
        json.dump(doc, f, indent=2)


if __name__ == '__main__':
    main()
