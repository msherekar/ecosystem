import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  root: '.',
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src/ui-react'),
    },
  },
  server: {
    port: 3000,
    strictPort: true,
  },
  // Ensure compatibility with Electron
  optimizeDeps: {
    exclude: ['electron']
  }
})
