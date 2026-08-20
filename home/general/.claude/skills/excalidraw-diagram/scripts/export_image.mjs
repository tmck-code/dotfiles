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

const execFileAsync = promisify(execFile);

const [, , inputPath, outputPath] = process.argv;
if (!inputPath || !outputPath) {
  console.error("Usage: export_image.mjs <input.excalidraw> <output.svg|output.png>");
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

const { exportToSvg } = await import("@excalidraw/utils");

const data = JSON.parse(await readFile(inputPath, "utf-8"));

const svg = await exportToSvg({
  elements: data.elements,
  appState: { ...(data.appState ?? {}), exportWithDarkMode: false },
  files: data.files || null,
  // Real font loading needs a browser FontFace API that jsdom doesn't
  // provide; skip it so headless export doesn't crash. Text still renders
  // (browser/OS fallback font), just not the exact embedded webfont.
  skipInliningFonts: true,
});

const ext = path.extname(outputPath).toLowerCase();

if (ext === ".svg") {
  await writeFile(outputPath, svg.outerHTML);
  console.log(`Wrote ${outputPath}`);
} else if (ext === ".png") {
  const svgPath = outputPath.replace(/\.png$/i, ".svg");
  await writeFile(svgPath, svg.outerHTML);
  try {
    await execFileAsync("rsvg-convert", [svgPath, "-o", outputPath]);
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
