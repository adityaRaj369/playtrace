import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: "./" keeps asset and data URLs relative so the same Vercel build also
// works in local preview without per-host path configuration.
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: { outDir: "dist", assetsDir: "assets" },
});
