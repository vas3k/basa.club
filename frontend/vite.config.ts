import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Must match DJANGO_VITE["default"]["static_url_prefix"]. Output lives in frontend/static/dist.
const BASE = "/static/dist/";
const DEV_SERVER_PORT = 5173;

export default defineConfig({
    plugins: [react()],
    base: BASE,
    server: {
        host: "0.0.0.0",
        port: DEV_SERVER_PORT,
        strictPort: true,
        origin: `http://localhost:${DEV_SERVER_PORT}`,
    },
    build: {
        outDir: "static/dist",
        emptyOutDir: true,
        manifest: true,
        rollupOptions: {
            input: "src/main.ts",
        },
    },
});
