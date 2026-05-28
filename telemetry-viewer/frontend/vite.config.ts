import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");

  return {
    plugins: [react()],
    server: {
      port: 3001,
      proxy: {
        "/api/analysis-service": {
          target: env.VITE_DEV_ANALYSIS_API_PROXY_TARGET ?? "http://127.0.0.1:8010",
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/analysis-service/, ""),
        },
        "/api/telemetry-source": {
          target: env.VITE_DEV_TELEMETRY_SOURCE_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/telemetry-source/, ""),
        },
      },
    },
  };
});
