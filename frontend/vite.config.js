import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// src/api.js calls relative paths (/api/v1, /health), which nginx proxies in
// the container. `npm run dev` has no nginx, so without this proxy every
// request from the dev server hits Vite itself and 404s.
const backend = process.env.VITE_BACKEND_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  test: {
    setupFiles: ['./src/test/setup.js'],
  },
  build: {
    // Two entries, because the two halves of the site have opposite needs.
    // `index.html` is the landing page: static, zero JavaScript, indexable —
    // its copy has to sit in the served HTML for a crawler to read it. The
    // React app moves under /app/, which robots.txt disallows.
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        app: resolve(__dirname, "app/index.html"),
      },
    },
  },
  server: {
    proxy: {
      "/api": { target: backend, changeOrigin: true },
      "/health": { target: backend, changeOrigin: true },
    },
  },
});
