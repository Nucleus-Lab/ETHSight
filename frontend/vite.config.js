import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // Allow listening on all network interfaces
    port: 5173,        // The port Vite should run on
    allowedHosts: [
      'nucleuslab.xyz',  // Allow requests from your domain
      'localhost',        // Allow local development
      '127.0.0.1',        // Allow local IP
    ],
  },
})
