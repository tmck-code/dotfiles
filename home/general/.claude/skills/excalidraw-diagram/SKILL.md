---
name: excalidraw-diagram
description: Convert a mermaid `classDiagram` (with `direction LR`), `erDiagram`, `flowchart`/`graph`, `gantt`, or `pie` into an Excalidraw `.excalidraw` file styled to match hand-drawn diagram conventions (elbow arrows, UML class boxes, ERD tables, rounded flowchart nodes, gantt timeline bars or pie wedges, pastel fills, left-aligned text), and render that `.excalidraw` file to a PNG/SVG screenshot. Use when the user wants a diagram, ER/database schema diagram, flowchart/architecture diagram, gantt/timeline chart, or pie chart (from a mermaid diagram, code, or a prompt) turned into an editable Excalidraw file, or wants a screenshot/image of an existing `.excalidraw` file.
---

# Excalidraw Diagram

Generates and renders Excalidraw diagrams. Generation always goes through
mermaid as the intermediate — direct prompt/code → `.excalidraw` (skipping
mermaid) is a planned future addition, not yet implemented; don't imply it
works. `convert.py` picks its path from the input's diagram directive:

| Input | Output |
| --- | --- |
| `classDiagram` | pastel UML class boxes + composition arrows |
| `erDiagram` | ERD tables + crowfoot relationship arrows |
| `flowchart` / `graph` | rounded nodes, subgraph containers, labelled arrows |
| `gantt` | section bands, unit grid, rounded task bars, axis ticks, title pill |
| `pie` | filled wedges, in-slice percentages, swatch legend |

### classDiagram → UML boxes

Each mermaid `class` becomes a UML-style box (rectangle + title text +
divider line + member text), and each composition edge (`*--` / `--*`)
becomes an elbowed arrow with a diamond at the "owner" end, bound to the two
boxes' rectangles.

Styling (font, box padding, member-line spacing, elbow routing, diamond
placement) was reverse-engineered from a hand-converted reference diagram of
this exact kind. Boxes are colored from a small pastel palette, cycled per
box; no attempt is made to match colors to specific box roles.

### erDiagram → ERD tables

Each entity becomes a database-table box: a colored header band with the
entity's white centered title, a matching light body tint, and one monospace
row per attribute separated by grey (`#ced4da`) full-width divider lines.
Rows are `name`/`type`/`key` space-padded into aligned columns and colored by
key — PK `#e67700`, UK `#2f9e44`, FK `#c92a2a`, plain `#1e1e1e`. Header/tint
pairs cycle per entity from a six-colour palette.

Relationships become elbowed arrows bound to both tables, with crowfoot
arrowheads mapped from the mermaid cardinality (`||` → one, `|o`/`o|` →
zero-or-one, `}o`/`o{` → many, `}|`/`|{` → one-or-many); a `..` link renders
dashed, `--` solid, and the `: "label"` becomes a bound arrow label.

This styling was reverse-engineered from a hand-drawn ERD reference
diagram, which contained two equivalent table styles; the tinted-body one
("style B") is what's implemented. Its
geometry was drawn at a large zoom, so every constant in `scripts/convert.py`
is expressed as a ratio of `ERD_ROW_FONT` (see the `ERD_*` block).

See `example-erd.mmd` for a worked input.

### flowchart → boxes and arrows

Each node becomes a shape (rounded rectangle by default) with its label
centre-bound inside it, coloured from `classDef`/`class`/`style` if the
diagram declares any and left neutral otherwise; a diagram that declares no
styles at all gets the pastel palette cycled over its nodes instead. Each
`subgraph` becomes a dashed rounded container drawn behind its members, with
its title sitting *above* the container's top edge and flush to its left
edge (as in the hand-drawn reference).

Styling here is taken from the decision tree in the same reference diagram:
`FONT_FAMILY = 8` (Comic Shanns; used for node labels, edge labels and
cluster titles alike), 8px corner radius, a saturated stroke over a matching
pale fill, and the label in the stroke colour.

Layout collapses every subgraph to a single node of a *cluster graph* and
runs the same longest-path column assignment over that, so a subgraph's
members always stay together in one column and containers never interleave.
Cycles are broken deterministically — edges are taken in declaration order
and any that would close a cycle is dropped — so both the column assignment
and the intra-cluster member order (by longest-path depth) describe the
diagram's flow and don't vary between runs.

Spacing is derived from what has to fit in it:

- the vertical gap between two stacked members is `NODE_GAP` (46) for an
  unlabelled edge, grown to the edge label's height + `2 * LABEL_PAD` when
  the two are joined by a labelled edge;
- the horizontal gutter between two columns is `COL_GAP` (150) or, if wider,
  the widest label on an edge crossing that gutter plus label and routing
  padding;
- long edge labels are word-wrapped to `EDGE_LABEL_WRAP` (24) chars, which
  both stops them sticking out sideways over neighbouring boxes and keeps the
  gutters sane;
- the vertical gap above a titled cluster reserves the title band
  (`TITLE_TEXT_H + TITLE_GAP`), since the title now lives outside the box.

Arrows are routed by an obstacle-avoiding orthogonal router
(`route()`/`_shortest()`): every node box except the two endpoints, every
cluster title, and every cluster container that belongs to neither endpoint
is inflated by `ROUTE_MARGIN` and treated as solid; candidate lanes are those
inflated edges, the endpoints' anchor stubs, and a ring `ROUTE_RING` outside
the whole diagram bbox (so a route can go all the way around). Dijkstra over
that lane grid minimises length + `TURN_PENALTY` per elbow across all 16
side-anchor pairs, biased toward anchors that face the other endpoint.
Arrows are emitted as Excalidraw's native elbow arrows (`elbowed: true`) with
both bindings kept, so a later hand-nudge in the app re-routes orthogonally
instead of collapsing back to a diagonal.

See `example-flowchart.mmd` / `.png` for a worked input — subgraphs, a
cylinder node, `<br/>` labels, `classDef`, and `linkStyle`.

### gantt → banded timeline

Each `section` becomes a full-width band tinted from a (bar fill, band
tint) palette cycled per section, with the section name wrapped (and
hyphenated if a word is too long) into a label column on the left. Each
task gets its own row inside its band and is drawn as a rounded solid bar
(`GANTT_UNIT_W` = 95 px per axis unit, 31 px tall, 2 px stroke). The task
name is centred inside the bar when it fits; otherwise it is set to the
right of the bar in a smaller face over a band-tinted backing rectangle so
it stays readable across the grid lines. One vertical grid line per axis
unit spans all bands, with a tick label beneath (zero-padded to two digits
for `%S`/`%M`/`%H` `axisFormat`s), and the `title` sits in a hand-drawn
(roughness 2) pill above the chart.

Styling was reverse-engineered from a hand-converted reference of this
exact kind; the constants live in the `GANTT_*` block of
`scripts/gantt.py`. See `example-gantt.mmd` / `.png` for a worked input.

### pie → filled wedges

Values are normalised to fractions of their total and drawn clockwise from 12
o'clock into a `PIE_RADIUS`-radius circle. Each slice is a solid-filled
`line` element whose points run centre → rim → arc samples (every
`PIE_ARC_STEP` degrees) → centre, so it stays a closed wedge if it is nudged
in the app; the base ellipse underneath carries the last slice's fill, so any
seam between wedges shows that colour rather than white. Slice colours cycle
`PIE_PALETTE`.

Each slice gets its percentage centred on its mid-angle at
`PIE_SLICE_LABEL_R` of the radius — a narrow slice is only as wide as its
chord there, so the label slides outward (capped at `PIE_SLICE_LABEL_R_MAX`)
until the chord can hold it and then shrinks its face down to a
`PIE_SLICE_MIN_FONT` floor; slices under `PIE_MIN_LABEL_SWEEP` degrees get no
label at all. A legend of colour swatches plus labels sits to the right of the circle,
vertically centred on it. `showData` puts the raw value in the legend label
alongside the name; `title` is a plain centred line above the whole chart (the
reference has no title pill).

Styling was reverse-engineered from a hand-drawn reference pie (roughness 1,
1px black stroke, solid fills); the constants live in the `PIE_*` block of
`scripts/pie.py`. See `example-pie.mmd` / `.png` for a worked input.

## Quick start

```bash
python3 .claude/skills/excalidraw-diagram/scripts/convert.py <input.mmd> <output.excalidraw>
```

Open the output in https://excalidraw.com (or the desktop/VS Code app) via
File → Open.

## Scope

### classDiagram

Only supports:

- `classDiagram` with `direction LR`
- `class Id["Label"] { +member ... }` or bare `class Id` (no body)
- composition edges: `A *-- B` (diamond at A) or `A --* B` (diamond at B)

Layering (left-to-right columns) is computed from longest-path depth from
root nodes (nodes with no incoming edge); boxes within a column are stacked
and vertically centered. Other mermaid diagram types (flowchart, sequence,
ER, etc.) and other edge styles (inheritance `<|--`, association `-->`,
aggregation `o--`) are **not** supported by this path — extend
`parse_mermaid` / `EDGE_RE` in `scripts/convert.py` if you need them.

### flowchart

Supports `flowchart`/`graph` with any direction keyword (the keyword is
parsed but ignored — layout is always left-to-right), and:

- shapes `[x]`, `(x)`, `([x])`, `[[x]]`, `[(x)]`, `((x))`, `{x}`, `{{x}}`,
  `>x]`, with or without quotes, and `<br/>` for line breaks
- `subgraph ID["Title"] ... end`, including nesting (a nested subgraph's
  members are laid out in the innermost one)
- links `-->`, `---`, `-.->`, `-.-`, `==>`, `===`, `->`, with `|label|` or
  the `-- label -->` form
- `classDef`, `class`, `style` (`fill`, `stroke`, `stroke-width`) and
  `linkStyle <indices> stroke:...,stroke-width:...`

Not supported: `direction` inside a subgraph, edge chains
(`A --> B --> C`), multi-target edges (`A --> B & C`), `click`/`href`, and
mermaid's remaining shape and link syntaxes. Excalidraw has no cylinder
shape, so `[(db)]` renders as a rounded rectangle.

### erDiagram

Supports:

- `ENTITY { <type> <name> [PK|FK|UK[, ...]] ["comment"] }` attribute blocks
  (mermaid's type-then-name order; rendered name-then-type), bare `ENTITY`,
  and the `ENTITY["label"]` alias form
- relationships `A <card>--<card> B : label` and the dotted `..` variant,
  with cardinalities `||`, `|o`/`o|`, `}o`/`o{`, `}|`/`|{`

Attribute comments are parsed but not rendered. Columns are laid out
left-to-right by the same longest-path depth rule as `classDiagram`, and an
arrow is always drawn from the left-hand column to the right-hand one
(cardinalities swap with it, so the crowfoot stays on the correct entity).

### gantt

Supports `title`, `axisFormat`, `section`, and tasks of the form
`name : [tags,] [id,] [start,] end|duration` where `start` is a plain
number or `after <id>` (omitted → previous task's end), a bare-number `end`
is absolute and a suffixed one (`5s`, `2d`) is a duration. `dateFormat` is
parsed but ignored: times are always treated as plain numbers on a unit
axis, so real calendar dates (`2024-01-01`) are **not** supported. Tags
(`done`/`active`/`crit`/`milestone`) are accepted and ignored — every bar
is drawn the same way. `excludes`, `todayMarker`, `tickInterval` and
`weekday` are skipped.

### pie

Supports `pie` / `pie showData`, an optional `title`, and slices of the form
`"Label" : <number>`. The label must be quoted (mermaid's own requirement).
Negative values are not meaningful and are not guarded against. A one-slice
pie draws as a bare filled circle, since a 100% wedge is degenerate.

## Notes

- Box width/height and text-line spacing are heuristics calibrated against
  the hand-drawn reference's real element geometry (see constants at the top of
  `scripts/convert.py`: `CHAR_W`, `MEMBER_LINE_H`, `BASE_HEIGHT`, etc.), not
  an exact text-measurement engine — expect a few px of slack, same as the
  hand-converted reference.
- `classDiagram`/`erDiagram` arrow routing is simple Manhattan (two elbows),
  not pixel-identical to a hand-drawn version, but valid elbowed excalidraw
  arrows bound to both rectangles. `flowchart` uses the obstacle-avoiding
  router described above instead.
- Excalidraw (and the headless export) repositions a *bound* arrow label onto
  the arrow's own route midpoint, so the longest-segment position the
  generator writes into the label's `x`/`y` is advisory only. The gap sizing
  above is what actually keeps labels off the boxes.
- The flowchart router's anchors are the midpoints of a node's bounding-box
  sides, so on a diamond or ellipse an arrow leaves near the bbox corner;
  Excalidraw's binding tidies this up when the shape is dragged.

## Rendering to an image (screenshot)

`scripts/export_image.mjs` renders any `.excalidraw` file to SVG and/or PNG,
headlessly (no browser needed) via Excalidraw's own official export API
(`@excalidraw/utils`'s `exportToSvg`, run under jsdom).

**Always print the `file://` URL of every PNG/SVG produced**, as the last
step of the render — resolve the output path to absolute
(`realpath <output>`) and print `file://<absolute-path>`, one line per file.
Do this whether the render came from the Docker route or the local npm
route, and do it even when the user didn't ask for the path explicitly.

### Recommended: Docker

Avoids installing Node/npm/`rsvg-convert` on the host. The container only
ever writes into the directory you bind-mount — it never writes "real"
output anywhere else — so afterwards you move/copy the produced file(s)
wherever you want (e.g. into `.scratch/` for throwaway work, or straight to
their final destination).

The build context must contain real files: if the skill's `scripts/*` are
symlinks (e.g. into a dotfiles repo), `COPY` follows the build context rather
than the link and the build fails — `cp -L` the skill into a temp dir and
build from there.

```bash
docker build -t excalidraw-diagram-export .claude/skills/excalidraw-diagram

# bind-mount the directory holding your input, output paths are relative to it
docker run --rm -v "$(pwd):/data" excalidraw-diagram-export \
  .claude/skills/excalidraw-diagram/example-output.excalidraw \
  .scratch/example-output.png
```

Both the input and output paths are resolved relative to whatever host
directory you bind-mount to `/data` (the repo root in the example above).
Use `.svg` as the output extension for SVG instead of PNG.

### Fallback: local npm install

```bash
cd .claude/skills/excalidraw-diagram/scripts
npm install   # first time only — installs @excalidraw/utils + jsdom locally
node export_image.mjs ../example-output.excalidraw ../example-output.png
# or: node export_image.mjs ../example-output.excalidraw ../example-output.svg
```

Requirements:

- Node.js + npm with registry access, to install `@excalidraw/utils` and
  `jsdom` into `scripts/node_modules` (one-time `npm install`, not committed).
- For `.png` output: the `rsvg-convert` CLI (from `librsvg`) on `PATH`, used
  to rasterize the SVG that `exportToSvg` produces. `.svg` output has no
  extra dependency beyond the npm packages. If `rsvg-convert` is missing,
  the script still writes the `.svg` next to the requested `.png` path and
  tells you to rasterize it yourself (e.g. `inkscape`, ImageMagick
  `convert`/`magick`) — or just use the Docker route above, which bundles
  `rsvg-convert`.

### Both routes

- ERD tables rely on Excalidraw's monospace face (`fontFamily: 3`) to keep
  their name/type/key columns aligned. The headless export has no such font
  (see below), so exported ERD rows look ragged even though they line up
  perfectly in Excalidraw itself — don't "fix" the padding based on a PNG.
- jsdom has no `FontFace` API, so font inlining is skipped
  (`skipInliningFonts: true`); instead `export_image.mjs` points fontconfig
  at the skill's bundled `fonts/` dir (Excalifont, Comic Shanns — sources in
  `fonts/README.md`) before calling `rsvg-convert`, so both routes render
  the real faces with no font install. Fonts there must be `.ttf`/`.otf` —
  rsvg cannot load `.woff2`.
