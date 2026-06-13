import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // File/media routes are proxied to the Django backend so <img src="/uploads/...">
    // and downloads keep working without absolute URLs.
    proxy: {
      '/uploads': 'http://localhost:5051',
      '/deliverables': 'http://localhost:5051',
      '/api/hero-img': 'http://localhost:5051',
      '/api/preview-img': 'http://localhost:5051',
    },
  },
});
