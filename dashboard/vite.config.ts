import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,                 // bind 0.0.0.0 so a tunnel/LAN can reach it
    allowedHosts: true,         // accept the *.trycloudflare.com tunnel host
    proxy: {
      "/api": { target: "http://localhost:9000", changeOrigin: true, ws: true, rewrite: p => p.replace(/^\/api/, "") },
    },
  },
});
