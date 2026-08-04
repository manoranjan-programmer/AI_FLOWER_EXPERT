import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_BACKEND_URL || env.VITE_API_BASE_URL || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        // Original FastAPI Backend proxies (port 8000)
        '/predict': { target: backendTarget, changeOrigin: true },
        '/auth': { target: backendTarget, changeOrigin: true },
        '/chat/stream': {
          target: backendTarget,
          changeOrigin: true,
          ws: true,
          configure: (proxy) => {
            proxy.on('proxyRes', (proxyRes) => {
              proxyRes.headers['x-no-compression'] = '1'
              proxyRes.headers['cache-control'] = 'no-cache, no-transform'
            })
          },
        },
        '/chat': { target: backendTarget, changeOrigin: true },
        '/translate': { target: backendTarget, changeOrigin: true },
        '/health': { target: backendTarget, changeOrigin: true },
        '/history': { target: backendTarget, changeOrigin: true },
        '/api': { target: backendTarget, changeOrigin: true },
        '/flower': { target: backendTarget, changeOrigin: true },
      },
    },
  }
})
