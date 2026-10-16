import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const pdfRoot = dirname(require.resolve("pdfjs-dist/package.json"));
const assetGroups = ["cmaps", "standard_fonts", "wasm", "iccs"];
// The same fixed package assets are served in dev and emitted for production.
const localPdfAssets = (): Plugin => ({
  name: "hustudy-local-pdf-assets",
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      const match = req.url?.split("?")[0].match(/^\/pdfjs-assets\/(cmaps|standard_fonts|wasm|iccs)\/([a-zA-Z0-9_.-]+)$/);
      if (!match) return next();
      if (!readdirSync(join(pdfRoot, match[1])).includes(match[2])) { res.statusCode = 404; res.end(); return; }
      res.setHeader("Content-Type", match[2].endsWith(".wasm") ? "application/wasm" : match[2].endsWith(".js") ? "text/javascript" : "application/octet-stream");
      res.end(readFileSync(join(pdfRoot, match[1], match[2])));
    });
  },
  generateBundle() {
    for (const group of assetGroups) for (const file of readdirSync(join(pdfRoot, group))) {
      this.emitFile({type: "asset", fileName: `pdfjs-assets/${group}/${file}`, source: readFileSync(join(pdfRoot, group, file))});
    }
  }
});
export default defineConfig({ plugins: [react(), localPdfAssets()] });
