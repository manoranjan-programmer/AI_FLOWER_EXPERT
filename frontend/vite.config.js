import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_BACKEND_URL || env.VITE_API_BASE_URL || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        // Proxy API calls to FastAPI backend configured via .env
        '/auth': { target, changeOrigin: true },
        '/chat/stream': {
          target,
          changeOrigin: true,
          ws: true,
          configure: (proxy) => {
            proxy.on('proxyRes', (proxyRes) => {
              proxyRes.headers['x-no-compression'] = '1'
              proxyRes.headers['cache-control'] = 'no-cache, no-transform'
            })
          },
        },
        '/predict': { target, changeOrigin: true },
        '/chat': { target, changeOrigin: true },
        '/translate': { target, changeOrigin: true },
        '/health': { target, changeOrigin: true },
        '/history': { target, changeOrigin: true },
        '/api': { target, changeOrigin: true },
        '^/flower($|\\?)': {
          target: target,
          changeOrigin: true,
        },
      },
    },
  }
})
