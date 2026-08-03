import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const chatbotTarget = env.VITE_CHATBOT_API || env.VITE_BACKEND_URL || env.VITE_API_BASE_URL || 'http://localhost:8000'
  const classifierTarget = env.VITE_CLASSIFIER_API || 'http://localhost:8001'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        // Classifier microservice proxy
        '/predict': { target: classifierTarget, changeOrigin: true },

        // Chatbot microservice proxy
        '/auth': { target: chatbotTarget, changeOrigin: true },
        '/chat/stream': {
          target: chatbotTarget,
          changeOrigin: true,
          ws: true,
          configure: (proxy) => {
            proxy.on('proxyRes', (proxyRes) => {
              proxyRes.headers['x-no-compression'] = '1'
              proxyRes.headers['cache-control'] = 'no-cache, no-transform'
            })
          },
        },
        '/chat': { target: chatbotTarget, changeOrigin: true },
        '/translate': { target: chatbotTarget, changeOrigin: true },
        '/health': { target: chatbotTarget, changeOrigin: true },
        '/history': { target: chatbotTarget, changeOrigin: true },
        '/api': { target: chatbotTarget, changeOrigin: true },
        '/flower': { target: chatbotTarget, changeOrigin: true },
      },
    },
  }
})
