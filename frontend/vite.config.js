import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5183,
    // File/media routes are proxied to the Django backend so <img src="/uploads/...">
    // and downloads keep working without absolute URLs.
    proxy: {
      '/uploads': 'http://localhost:8061',
      '/deliverables': 'http://localhost:8061',
      '/api/hero-img': 'http://localhost:8061',
      '/api/preview-img': 'http://localhost:8061',
    },
  },
});
