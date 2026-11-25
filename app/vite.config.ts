import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// VITE_BASE is set by the deploy workflow to "/<repo>/" for GitHub Pages.
export default defineConfig({
  base: process.env.VITE_BASE ?? "/",
  plugins: [react(), tailwindcss()],
  // The app imports the engine's insulation-materials table (repo root is one
  // level up); allow the dev server to serve files from there.
  server: { fs: { allow: [".."] } },
});
