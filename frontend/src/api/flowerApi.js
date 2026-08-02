/**
 * flowerApi.js
 * Centralised Axios-based API client for Flower AI Expert.
 * All backend calls go through this module.
 */

import axios from 'axios'

// In development mode (Vite dev server), use relative path '' so requests are same-origin
// and proxied by Vite to the backend URL in .env. This prevents Chrome cross-origin stream buffering.
const isDev = import.meta.env.DEV
const rawBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
const BASE_URL = isDev ? '' : rawBaseUrl.replace(/\/+$/, '')

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,   // 2 min – LLM generation can be slow on CPU
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// --------------------------------------------------------------------------
// Request / response interceptors
// --------------------------------------------------------------------------
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred.'
    return Promise.reject(new Error(message))
  },
)

// --------------------------------------------------------------------------
// Auth API methods
// --------------------------------------------------------------------------

/**
 * Authenticate with Google OAuth 2.0 credential string (ID Token).
 * @param {string} credential
 * @returns {Promise<{ status: string, token: string, user: object }>}
 */
export async function loginWithGoogleApi(credential) {
  const response = await api.post('/auth/google', { credential })
  return response.data
}

/**
 * Fetch current authenticated user profile.
 * @returns {Promise<{ status: string, user: object }>}
 */
export async function fetchCurrentUserApi() {
  const response = await api.get('/auth/me')
  return response.data
}

/**
 * Logout current user session and clear cookies.
 * @returns {Promise<{ status: string, message: string }>}
 */
export async function logoutApi() {
  const response = await api.post('/auth/logout')
  return response.data
}

// --------------------------------------------------------------------------
// AI & Application API methods
// --------------------------------------------------------------------------

/**
 * Upload a flower image for classification.
 * @param {File} imageFile
 * @param {function} onUploadProgress  – optional progress callback (pct: number)
 * @returns {Promise<{ flower, confidence, summary, card }>}
 */
export async function predictFlower(imageFile, onUploadProgress) {
  const formData = new FormData()
  formData.append('file', imageFile)

  const response = await api.post('/predict', formData, {
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
 * Send a chat message about the current flower.
 * @param {string} message
 * @returns {Promise<{ answer: string }>}
 */
export async function sendChatMessage(message) {
  const response = await api.post('/chat', { message })
  return response.data
}

/**
 * Send a chat message with real-time ChatGPT-style token streaming.
 * @param {string} message
 * @param {function(string): void} onToken
 * @param {function(Error): void} onError
 * @param {function(): void} onDone
 */
export async function streamChatMessage(message, onToken, onError, onDone) {
  try {
    const directHost = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
    const url = `${directHost.replace(/\/+$/, '')}/chat/stream`
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })

    if (!response.ok) {
      const errText = await response.text()
      let errMsg = 'Failed to connect to streaming response.'
      try {
        const parsed = JSON.parse(errText)
        errMsg = parsed.detail || parsed.message || errMsg
      } catch (e) {
        if (errText) errMsg = errText
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
          // Ignore empty lines or SSE comment lines (like : ping)
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
            // handle error
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

/**
 * Translate text to a target language offline.
 * @param {string} text
 * @param {string} language  – ISO 639-1 code: "ta" | "hi" | "ml" | "en"
 * @returns {Promise<{ translated: string, language: string }>}
 */
export async function translateText(text, language) {
  const response = await api.post('/translate', { text, language })
  return response.data
}

/**
 * Health check.
 * @returns {Promise<{ status: string, flower: string|null }>}
 */
export async function healthCheck() {
  const response = await api.get('/health')
  return response.data
}

/**
 * Fetch search history records from MongoDB Atlas.
 */
export async function fetchHistory() {
  const response = await api.get('/history')
  return response.data
}

/**
 * Save chat session history to MongoDB Atlas.
 */
export async function saveHistorySession(sessionData) {
  const response = await api.post('/history/save', sessionData)
  return response.data
}

/**
 * Submit structured user feedback (Like/Dislike, Star Rating, Reasons, Comments) to MongoDB Chatbot_Feedback.
 * @param {object} feedbackData
 * @returns {Promise<{ status: string, feedback_id: string, message: string }>}
 */
export async function submitFeedbackApi(feedbackData) {
  const response = await api.post('/api/analytics/feedback', feedbackData)
  return response.data
}

export default api
