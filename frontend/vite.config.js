import process from 'node:process'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// scripts/run.ps1 sets FUNDEXPERT_API_PORT when the API is not on 8000.
const apiPort = process.env.FUNDEXPERT_API_PORT || '8000'
const apiProxy = { '/api': `http://127.0.0.1:${apiPort}` }

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: apiProxy,
  },
  preview: {
    proxy: apiProxy,
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    pool: 'threads',
    setupFiles: './src/test/setup.js',
  },
})
