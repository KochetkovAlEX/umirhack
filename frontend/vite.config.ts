import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Dev: Vite на :5173 проксирует /api и /media на Django (:8000).
// Prod: `npm run build` -> dist/, который отдаёт Django (один процесс, один порт).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: process.env.VITE_API_TARGET || 'http://localhost:8000', changeOrigin: true },
      '/media': { target: process.env.VITE_API_TARGET || 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: { outDir: 'dist', emptyOutDir: true, sourcemap: false },
})
