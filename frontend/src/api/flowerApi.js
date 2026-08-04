/**
 * flowerApi.js
 * Unified Axios & Fetch API client for Flower AI Expert.
 * Direct connection to the original FastAPI backend (port 8000).
 */

import axios from 'axios'

const isDev = import.meta.env.DEV

const rawBackendUrl = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_BASE_URL || ''
const BASE_URL = isDev ? '' : rawBackendUrl.replace(/\/+$/, '')

const backendApi = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,   // 2 min – LLM generation & inference on CPU
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// Response interceptor for consistent error handling
const handleResponseError = (error) => {
  const message =
    error.response?.data?.detail ||
    error.response?.data?.message ||
    error.message ||
    'An unexpected error occurred.'
  return Promise.reject(new Error(message))
}

backendApi.interceptors.response.use((res) => res, handleResponseError)

// Attach stored JWT token as Authorization Bearer header on every request
// Fallback for cross-origin deployments where HTTP-only cookies are blocked
backendApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('flower_ai_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// --------------------------------------------------------------------------
// Auth API methods (Original FastAPI Backend)
// --------------------------------------------------------------------------

export async function loginWithGoogleApi(credential) {
  const response = await backendApi.post('/auth/google', { credential })
  if (response.data?.token) {
    localStorage.setItem('flower_ai_token', response.data.token)
  }
  return response.data
}

export async function fetchCurrentUserApi() {
  const response = await backendApi.get('/auth/me')
  return response.data
}

export async function logoutApi() {
  const response = await backendApi.post('/auth/logout')
  localStorage.removeItem('flower_ai_token')
  return response.data
}

// --------------------------------------------------------------------------
// Flower Prediction & Identification API
// --------------------------------------------------------------------------

/**
 * Upload a flower image for classification to original FastAPI backend (port 8000).
 * The original backend performs prediction, knowledge retrieval, and MongoDB history saving in one step.
 * @param {File} imageFile
 * @param {function} onUploadProgress – optional progress callback (pct: number)
 * @returns {Promise<{ session_id: string, flower: string, confidence: number, summary: string, card: object }>}
 */
export async function predictFlower(imageFile, onUploadProgress) {
  const formData = new FormData()
  formData.append('file', imageFile)

  const response = await backendApi.post('/predict', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onUploadProgress
      ? (evt) => {
          const pct = Math.round((evt.loaded * 100) / (evt.total || 1))
          onUploadProgress(pct)
        }
      : undefined,
  })

  return response.data
}

/**
 * Legacy flower context selection helper for UI navigation.
 */
export async function selectFlowerApi(flowerName, confidence = 98.5, filename = '', imagePreview = '') {
  // Original backend tracks active flower context per session directly in /predict and /chat
  return { status: 'ok', flower: flowerName }
}

// --------------------------------------------------------------------------
// Chatbot & Streaming APIs
// --------------------------------------------------------------------------

/**
 * Send a chat message about the current flower to original FastAPI backend (port 8000).
 * @param {string} message
 * @returns {Promise<{ answer: string }>}
 */
export async function sendChatMessage(message) {
  const response = await backendApi.post('/chat', { message })
  return response.data
}

/**
 * Send a chat message with real-time token streaming via Server-Sent Events (SSE).
 */
export async function streamChatMessage(message, onToken, onError, onDone) {
  try {
    const rawHost = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_BASE_URL || ''
    const baseUrl = isDev ? '' : rawHost.replace(/\/+$/, '')
    const url = `${baseUrl}/chat/stream`

    let response
    try {
      const streamHeaders = { 'Content-Type': 'application/json' }
      const storedToken = localStorage.getItem('flower_ai_token')
      if (storedToken) {
        streamHeaders['Authorization'] = `Bearer ${storedToken}`
      }
      response = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: streamHeaders,
        body: JSON.stringify({ message }),
      })
    } catch (netErr) {
      throw new Error('Could not connect to FastAPI Backend on port 8000. Please ensure the original backend is running on http://localhost:8000.')
    }

    if (!response.ok) {
      const errText = await response.text()
      let errMsg = 'Failed to connect to streaming response.'
      if (response.status === 502 || response.status === 504) {
        errMsg = 'FastAPI Backend is offline on port 8000. Please start backend with: uvicorn app:app --port 8000'
      } else {
        try {
          const parsed = JSON.parse(errText)
          errMsg = parsed.detail || parsed.message || errMsg
        } catch (e) {
          if (errText) errMsg = errText
        }
      }
      throw new Error(errMsg)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || trimmed.startsWith(':')) {
          continue
        }
        if (trimmed.startsWith('data: ')) {
          const dataStr = trimmed.slice(6).trim()
          if (dataStr === '[DONE]') {
            if (onDone) onDone()
            return
          }
          try {
            const parsed = JSON.parse(dataStr)
            if (parsed.error) {
              throw new Error(parsed.error)
            }
            if (parsed.token && onToken) {
              onToken(parsed.token)
            }
          } catch (e) {
            if (e.message && e.message !== 'Unexpected token' && onError) {
              onError(e)
            }
          }
        }
      }
    }

    if (onDone) onDone()
  } catch (err) {
    if (onError) onError(err)
  }
}

// --------------------------------------------------------------------------
// Utilities, History & Analytics
// --------------------------------------------------------------------------

/**
 * Translate text to a target language offline.
 */
export async function translateText(text, language) {
  const response = await backendApi.post('/translate', { text, language })
  return response.data
}

/**
 * Health check.
 */
export async function healthCheck() {
  const response = await backendApi.get('/health')
  return response.data
}

/**
 * Fetch search history records from MongoDB Atlas.
 */
export async function fetchHistory() {
  const response = await backendApi.get('/history')
  return response.data
}

/**
 * Save chat session history to MongoDB Atlas.
 */
export async function saveHistorySession(sessionData) {
  const response = await backendApi.post('/history/save', sessionData)
  return response.data
}

/**
 * Submit structured user feedback.
 */
export async function submitFeedbackApi(feedbackData) {
  const response = await backendApi.post('/api/analytics/feedback', feedbackData)
  return response.data
}

export default backendApi
