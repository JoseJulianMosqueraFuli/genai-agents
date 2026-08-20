import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev we proxy API calls to the FastAPI backend so the browser talks to the
// same origin (no CORS needed locally). Override the target with VITE_API_TARGET.
const API_TARGET = process.env.VITE_API_TARGET ?? "http://localhost:8000";

export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            "/v1": { target: API_TARGET, changeOrigin: true },
            "/health": { target: API_TARGET, changeOrigin: true },
        },
    },
});
