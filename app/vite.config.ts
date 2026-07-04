import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// VITE_BASE is set by the deploy workflow to "/<repo>/" for GitHub Pages.
export default defineConfig({
  base: process.env.VITE_BASE ?? "/",
  plugins: [react()],
});
