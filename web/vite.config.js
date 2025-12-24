import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import path from "path"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    allowedHosts: ["dumontcloud-local.orb.local", ".orb.local"],
    // HMR config - use client's host automatically to prevent infinite polling
    hmr: {
      // Don't force a specific host - let the client use whatever host it connected with
      // This prevents WebSocket failures when accessing via localhost vs external hostname
      clientPort: 5173,
      protocol: "ws",
    },
    watch: {
      // Disable polling - use native file watching for better performance
      usePolling: false,
    },
    proxy: {
      "/admin/doc/live": {
        target: "http://192.168.139.80:8081",
        changeOrigin: true,
      },
      "/api/docs": {
        target: "http://192.168.139.80:8081",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/docs/, "/api"),
      },
      "/api": {
        target: "http://192.168.139.80:8000",
        changeOrigin: true,
      },
      "/admin": {
        target: "http://192.168.139.80:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "build",
  },
})
