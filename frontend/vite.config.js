import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"

export default defineConfig({
  plugins: [react()],
  // Read .env from the monorepo root (one .env for the whole project)
  envDir: '../',
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // In Docker on Windows/macOS the bind-mounted source sends no file events into the
  // container, so the dev server has to poll to notice edits (set in docker-compose.yml).
  server: {
    watch: process.env.VITE_WATCH_POLLING === "true" ? { usePolling: true, interval: 300 } : undefined,
  },
})