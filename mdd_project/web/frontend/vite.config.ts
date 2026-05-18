import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Production (Render): assets at site root; API via nginx /api proxy
  base: "/",
  server: {
    port: 5173,
    proxy: {
      // Proxy all /api/* → FastAPI on :8000
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
