#!/usr/bin/env node
// Render an .excalidraw JSON file to SVG (and optionally PNG) headlessly.
//
// Usage: node export_image.mjs <input.excalidraw> <output.svg|output.png>
//
// Requires @excalidraw/utils + jsdom to be installed in this script's
// directory (see package.json next to this file). PNG output additionally
// shells out to `rsvg-convert` to rasterize the SVG.

import { JSDOM } from "jsdom";
import { readFile, writeFile } from "fs/promises";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";
import { fileURLToPath } from "url";
import { existsSync, mkdtempSync, writeFileSync } from "fs";
import { tmpdir } from "os";

// Point fontconfig at the skill's bundled fonts/ dir (Excalifont, Comic
// Shanns) so rsvg-convert finds them without a system install. System fonts
// stay available as fallbacks via <include>.
function fontconfigEnv() {
  // skill layout: scripts/export_image.mjs + ../fonts; docker image: /work/export_image.mjs + /work/fonts
  const here = path.dirname(fileURLToPath(import.meta.url));
  const fontsDir = [path.resolve(here, "..", "fonts"), path.resolve(here, "fonts")].find(existsSync);
  if (!fontsDir) return process.env;
  const cacheDir = path.join(mkdtempSync(path.join(tmpdir(), "excalidraw-fc-")), "cache");
  const conf = path.join(path.dirname(cacheDir), "fonts.conf");
  writeFileSync(conf, `<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>${fontsDir}</dir>
  <cachedir>${cacheDir}</cachedir>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
</fontconfig>
`);
  return { ...process.env, FONTCONFIG_FILE: conf };
}

const execFileAsync = promisify(execFile);

const args = process.argv.slice(2);
const dark = args.includes("--dark");
const [inputPath, outputPath] = args.filter((a) => !a.startsWith("--"));
if (!inputPath || !outputPath) {
  console.error("Usage: export_image.mjs [--dark] <input.excalidraw> <output.svg|output.png>");
  process.exit(1);
}

// exportToSvg touches window/document/devicePixelRatio at module load time,
// so these globals must exist before the dynamic import below.
const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
global.window = dom.window;
global.document = dom.window.document;
global.devicePixelRatio = 1;
global.HTMLElement = dom.window.HTMLElement;
global.SVGElement = dom.window.SVGElement;
// jsdom has no canvas; exportToSvg still calls measureText for frame names
// and autoResize text. A width-only stub (≈0.6em per char) keeps it alive —
// element geometry comes from the file, so this only affects frame labels.
dom.window.HTMLCanvasElement.prototype.getContext = function () {
  const ctx = { font: "10px sans-serif" };
  ctx.measureText = (t) => {
    const px = parseFloat(ctx.font) || 10;
    return { width: t.length * px * 0.6 };
  };
  return ctx;
};

const { exportToSvg } = await import("@excalidraw/utils");

const data = JSON.parse(await readFile(inputPath, "utf-8"));
const DARK_BG = "#121212";

// Dark-mode post-pass. Only near-neutral colours (low saturation: the black
// strokes, grey fills, white/near-white node fills) are flipped along the
// lightness axis; anything with real hue (accent fills/strokes) is kept so
// the diagram's colour coding survives.
function darken(svgText) {
  const flip = (hex) => {
    let h = hex.slice(1);
    if (h.length === 3) h = h.split("").map((c) => c + c).join("");
    if (h.length !== 6) return hex;
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    if (max - min > 8) return hex;                        // has hue (even a tint): keep
    const v = 255 - Math.round((r + g + b) / 3);           // invert lightness
    const c = v.toString(16).padStart(2, "0");
    return `#${c}${c}${c}`;
  };
  const flipAll = (t) => t
    .replace(/(fill|stroke)="(#[0-9a-fA-F]{3,6})"/g, (_, k, hex) => `${k}="${flip(hex)}"`)
    .replace(/(fill|stroke):\s*(#[0-9a-fA-F]{3,6})/g, (_, k, hex) => `${k}:${flip(hex)}`);
  // the canvas rect (already DARK_BG) and <mask> cut-outs must not be flipped
  const i = svgText.indexOf("<rect");
  const j = svgText.indexOf(">", i) + 1;
  const body = svgText.slice(j).split(/(<mask[\s>][\s\S]*?<\/mask>)/)
    .map((part) => (part.startsWith("<mask") ? part : flipAll(part))).join("");
  return svgText.slice(0, j) + body;
}

// Frames are editor-only containers: exporting them adds their label and
// clips/pads the canvas to their bounds (an empty stray frame can blow the
// export up to thousands of px). Drop them and unlink their members.
const elements = data.elements
  .filter((el) => !el.isDeleted && el.type !== "frame" && el.type !== "magicframe")
  .map((el) => (el.frameId ? { ...el, frameId: null } : el));

const svg = await exportToSvg({
  elements,
  // --dark is applied as an SVG post-pass below: Excalidraw's own dark mode
  // is a root `filter: invert() hue-rotate()` that rsvg applies only
  // partially (arrows and labels vanish), so it is never enabled here
  appState: {
    ...(data.appState ?? {}),
    exportWithDarkMode: false,
    exportBackground: true,
    ...(dark ? { viewBackgroundColor: DARK_BG } : {}),
  },
  files: data.files || null,
  // Real font loading needs a browser FontFace API that jsdom doesn't
  // provide; skip it so headless export doesn't crash. Text still renders
  // (browser/OS fallback font), just not the exact embedded webfont.
  skipInliningFonts: true,
});

const svgOut = dark ? darken(svg.outerHTML) : svg.outerHTML;
const ext = path.extname(outputPath).toLowerCase();

if (ext === ".svg") {
  await writeFile(outputPath, svgOut);
  console.log(`Wrote ${outputPath}`);
} else if (ext === ".png") {
  const svgPath = outputPath.replace(/\.png$/i, ".svg");
  await writeFile(svgPath, svgOut);
  try {
    await execFileAsync("rsvg-convert", [svgPath, "-o", outputPath], { env: fontconfigEnv() });
  } catch (err) {
    console.error(
      "rsvg-convert failed or is not installed. SVG was written to " +
        svgPath +
        "; rasterize it yourself (rsvg-convert/inkscape/imagemagick) or install rsvg-convert.",
    );
    throw err;
  }
  console.log(`Wrote ${svgPath} and ${outputPath}`);
} else {
  console.error(`Unsupported output extension: ${ext} (use .svg or .png)`);
  process.exit(1);
}
