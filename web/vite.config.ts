import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

// Built assets are committed under jatayu/web/dist so the demo laptop needs no Node at runtime.
export default defineConfig({
  plugins: [preact()],
  build: { outDir: "../jatayu/web/dist", emptyOutDir: true, assetsInlineLimit: 0 },
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
