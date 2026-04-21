import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Keep localhost default for local development; can be overridden by env.
  const apiProxyTarget =
    process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
  // Must match FastAPI mount at /ui and BrowserRouter basename
  base: "/ui/",
  server: {
    host: "::",
    port: 8080,
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
    hmr: {
      overlay: false,
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    dedupe: ["react", "react-dom", "react/jsx-runtime", "react/jsx-dev-runtime", "@tanstack/react-query", "@tanstack/query-core"],
  },
  };
});
