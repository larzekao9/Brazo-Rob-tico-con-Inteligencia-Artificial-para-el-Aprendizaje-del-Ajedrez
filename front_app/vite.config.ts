import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import {defineConfig} from 'vite';

// BACKEND_URL permite apuntar el proxy a otro backend en desarrollo (por defecto el de :8000).
const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000';

// Mismo proxy que frontend/vite.config.ts, sin /facilitador ni /entrenamiento.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5174,
    proxy: {
      '/jugada': BACKEND_URL,
      '/analisis': BACKEND_URL,
      '/partida': BACKEND_URL,
      '/vision': BACKEND_URL,
      '/health': BACKEND_URL,
      '/aprendizaje': BACKEND_URL,
      '/auth': BACKEND_URL,
      '/simulacion': BACKEND_URL,
      '/usuario': BACKEND_URL,
      '/media': BACKEND_URL,
      '/tutor': BACKEND_URL,
    },
  },
});
