import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { resolve } from "path";
import { fileURLToPath } from "url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
      "@/pages": resolve(__dirname, "src/pages"),
      "@/components": resolve(__dirname, "src/components"),
      "@/hooks": resolve(__dirname, "src/hooks"),
      "@/services": resolve(__dirname, "src/services"),
      "@/types": resolve(__dirname, "src/types"),
      "@/assets": resolve(__dirname, "src/assets"),
      "@/styles": resolve(__dirname, "src/styles"),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
    },
  },
});
