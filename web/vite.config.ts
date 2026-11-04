import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Static build: relative base so the site also works from any local folder.
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: {
    outDir: "dist",
    chunkSizeWarningLimit: 900,
  },
  server: { port: 5173, strictPort: true },
});
