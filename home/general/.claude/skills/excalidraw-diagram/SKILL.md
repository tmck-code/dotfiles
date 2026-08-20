---
name: excalidraw-diagram
description: Convert a mermaid `classDiagram` (with `direction LR`) into an Excalidraw `.excalidraw` file styled to match the repo's hand-drawn diagram conventions (elbow arrows, UML class boxes, pastel fills, left-aligned text), and render that `.excalidraw` file to a PNG/SVG screenshot. Use when the user wants a diagram (from a mermaid class diagram, code, or a prompt) turned into an editable Excalidraw file, or wants a screenshot/image of an existing `.excalidraw` file.
---

# Excalidraw Diagram

Generates and renders Excalidraw diagrams. Today the only generation path is
mermaid `classDiagram` → `.excalidraw` JSON; direct prompt/code → `.excalidraw`
generation (skipping mermaid as an intermediate) is a planned future addition,
not yet implemented — don't imply it works.

Each mermaid `class` becomes a UML-style box (rectangle + title text +
divider line + member text), and each composition edge (`*--` / `--*`)
becomes an elbowed arrow with a diamond at the "owner" end, bound to the two
boxes' rectangles.

Styling (font, box padding, member-line spacing, elbow routing, diamond
placement) was reverse-engineered from `yas-structure.excalidraw` in the repo
root — the maintainer's hand-converted reference for this exact diagram
(from PR #120). Boxes are colored from a small pastel palette, cycled per
box; no attempt is made to match colors to specific box roles.

## Quick start

```bash
python3 .claude/skills/excalidraw-diagram/scripts/convert.py <input.mmd> <output.excalidraw>
```

Open the output in https://excalidraw.com (or the desktop/VS Code app) via
File → Open.

## Scope (v1)

Only supports:

- `classDiagram` with `direction LR`
- `class Id["Label"] { +member ... }` or bare `class Id` (no body)
- composition edges: `A *-- B` (diamond at A) or `A --* B` (diamond at B)

Layering (left-to-right columns) is computed from longest-path depth from
root nodes (nodes with no incoming edge); boxes within a column are stacked
and vertically centered. Other mermaid diagram types (flowchart, sequence,
ER, etc.) and other edge styles (inheritance `<|--`, association `-->`,
aggregation `o--`) are **not** supported — extend `parse_mermaid` /
`EDGE_RE` in `scripts/convert.py` if you need them.

## Notes

- Box width/height and text-line spacing are heuristics calibrated against
  the reference file's real element geometry (see constants at the top of
  `scripts/convert.py`: `CHAR_W`, `MEMBER_LINE_H`, `BASE_HEIGHT`, etc.), not
  an exact text-measurement engine — expect a few px of slack, same as the
  hand-converted reference.
- Arrow routing is simple Manhattan (two elbows), not pixel-identical to a
  hand-drawn version, but valid elbowed excalidraw arrows bound to both
  rectangles.

## Rendering to an image (screenshot)

`scripts/export_image.mjs` renders any `.excalidraw` file to SVG and/or PNG,
headlessly (no browser needed) via Excalidraw's own official export API
(`@excalidraw/utils`'s `exportToSvg`, run under jsdom).

### Recommended: Docker

Avoids installing Node/npm/`rsvg-convert` on the host. The container only
ever writes into the directory you bind-mount — it never writes "real"
output anywhere else — so afterwards you move/copy the produced file(s)
wherever you want (e.g. into `.scratch/` for throwaway work, or straight to
their final destination).

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

- Text is rendered with a fallback system font, not the exact embedded
  Excalidraw webfont — jsdom has no `FontFace`/font-loading API, so font
  inlining is skipped (`skipInliningFonts: true`). Geometry, colors, and
  layout are otherwise exact.
