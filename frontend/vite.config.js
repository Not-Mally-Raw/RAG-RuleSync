import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy all API calls through Vite's dev server to avoid CORS in development
      '/upload-document': 'http://localhost:8000',
      '/process-rules-taxonomy': 'http://localhost:8000',
      '/process-rules': 'http://localhost:8000',
    },
  },
})
