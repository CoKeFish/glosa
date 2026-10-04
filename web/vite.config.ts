import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: { "/api": process.env.API_URL ?? "http://api:8000" },
    // Bind-mounted sources on Windows don't emit file events inside the container.
    watch: { usePolling: true },
  },
});
