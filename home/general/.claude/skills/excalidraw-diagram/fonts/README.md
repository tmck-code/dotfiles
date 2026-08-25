Fonts used by the headless export (`fontconfig` needs real `.ttf`s;
`rsvg-convert` cannot load `.woff2`).

- `Excalifont-Regular.ttf` — decompressed (`woff2_decompress`) from
  https://excalidraw.nyc3.cdn.digitaloceanspaces.com/fonts/Excalifont-Regular.woff2
- `ComicShanns-Regular.ttf` — `v2/comic shanns 2.ttf` from
  https://github.com/shannpersand/comic-shanns

`export_image.mjs` loads these via a generated fontconfig file; no system
install is needed.
