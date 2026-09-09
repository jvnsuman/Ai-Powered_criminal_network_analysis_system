/**
 * dashboard/vite.config.js
 *
 * Proxies /api/* to the FastAPI backend (api/main.py, run via
 * `uvicorn api.main:app --reload`, default port 8000) so the
 * dashboard never has to deal with CORS in development.
 */

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
