import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: "./" keeps all asset + data URLs relative, so the same build works on
// GitHub Pages (served from /<repo>/), Vercel, Netlify, or a local file server
// without any per-host configuration.
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: { outDir: "dist", assetsDir: "assets" },
});
