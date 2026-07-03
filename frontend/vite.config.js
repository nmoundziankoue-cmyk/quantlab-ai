import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/quant': 'http://localhost:8001',
      '/m18': 'http://localhost:8001',
      '/research': 'http://localhost:8001',
      '/system': 'http://localhost:8001',
      '/market': 'http://localhost:8001',
      '/portfolio': 'http://localhost:8001',
    },
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-query': ['@tanstack/react-query', '@tanstack/react-query-devtools'],
          'vendor-charts': ['recharts', 'lightweight-charts'],
          'vendor-http': ['axios'],
          'vendor-state': ['zustand'],
        },
      },
    },
  },
})
