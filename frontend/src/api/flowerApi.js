/**
 * flowerApi.js
 * Dual-endpoint Axios API client for Flower AI Expert.
 * Routes image classification calls to backend-classifier and chatbot/auth/history calls to backend-chatbot.
 */

import axios from 'axios'

const isDev = import.meta.env.DEV

const rawChatbotUrl = import.meta.env.VITE_CHATBOT_API || import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_BASE_URL || ''
const rawClassifierUrl = import.meta.env.VITE_CLASSIFIER_API || ''

const CHATBOT_BASE_URL = isDev ? '' : rawChatbotUrl.replace(/\/+$/, '')
const CLASSIFIER_BASE_URL = isDev ? '' : rawClassifierUrl.replace(/\/+$/, '')

const chatbotApi = axios.create({
  baseURL: CHATBOT_BASE_URL,
  timeout: 120_000,   // 2 min – LLM generation can be slow on CPU
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

const classifierApi = axios.create({
  baseURL: CLASSIFIER_BASE_URL,
  timeout: 60_000,
  withCredentials: true,
})

// Response interceptors
const handleResponseError = (error) => {
  const message =
    error.response?.data?.detail ||
    error.response?.data?.message ||
    error.message ||
    'An unexpected error occurred.'
  return Promise.reject(new Error(message))
}

chatbotApi.interceptors.response.use((res) => res, handleResponseError)
classifierApi.interceptors.response.use((res) => res, handleResponseError)

// Attach stored JWT token as Authorization Bearer header on every chatbot request
// This is the fallback for production where cross-origin cookies may be blocked
chatbotApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('flower_ai_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// --------------------------------------------------------------------------
// Auth API methods (Chatbot microservice)
// --------------------------------------------------------------------------

export async function loginWithGoogleApi(credential) {
  const response = await chatbotApi.post('/auth/google', { credential })
  // Store JWT token for Bearer header fallback (production cross-origin deployments)
  if (response.data?.token) {
    localStorage.setItem('flower_ai_token', response.data.token)
  }
  return response.data
}

export async function fetchCurrentUserApi() {
  const response = await chatbotApi.get('/auth/me')
  return response.data
}

export async function logoutApi() {
  const response = await chatbotApi.post('/auth/logout')
  // Clear stored token on logout
  localStorage.removeItem('flower_ai_token')
  return response.data
}

function readFileAsDataUrl(file) {
  return new Promise((resolve) => {
    if (!file) return resolve('')
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target?.result || '')
    reader.onerror = () => resolve('')
    reader.readAsDataURL(file)
  })
}

/**
 * Upload a flower image for classification to backend-classifier (port 8001),
 * then notify backend-chatbot (port 8000) to set active context, save image preview, and fetch summary/card.
 * @param {File} imageFile
 * @param {function} onUploadProgress – optional progress callback (pct: number)
 * @returns {Promise<{ session_id, flower, confidence, summary, card }>}
 */
export async function predictFlower(imageFile, onUploadProgress) {
  const formData = new FormData()
  formData.append('file', imageFile)

  // Step 1: Send image to Classifier service (port 8001)
  const classifierResponse = await classifierApi.post('/predict', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onUploadProgress
      ? (evt) => {
          const pct = Math.round((evt.loaded * 100) / (evt.total || 1))
          onUploadProgress(pct)
        }
      : undefined,
  })

  const { flower_name, flower, confidence, session_id } = classifierResponse.data
  const predictedFlower = flower_name || flower || 'Unknown'

  // Step 2: Read base64 image preview for MongoDB history persistence
  const imagePreview = await readFileAsDataUrl(imageFile)
  const filename = imageFile?.name || 'flower.jpg'

  // Step 3: Notify Chatbot service (port 8000) to initialize active flower context, image preview, & card
  try {
    const selectResponse = await chatbotApi.post('/flower/select', {
      flower_name: predictedFlower,
      confidence: confidence,
      filename: filename,
      image_preview: imagePreview,
    })
    return selectResponse.data
  } catch (err) {
    console.warn('Chatbot service context sync fallback:', err)
    const normalizedFlower = (predictedFlower || 'flower').toLowerCase().replace(/ /g, '_')
    return {
      session_id: session_id || `session_${normalizedFlower}_${Date.now()}`,
      flower: predictedFlower,
      confidence: confidence || 98.5,
      summary: `Identified as ${predictedFlower}`,
      card: { flower_name: predictedFlower },
    }
  }
}

/**
 * Explicitly set active flower context on backend-chatbot (port 8000).
 */
export async function selectFlowerApi(flowerName, confidence = 98.5, filename = '', imagePreview = '') {
  try {
    const response = await chatbotApi.post('/flower/select', {
      flower_name: flowerName,
      confidence: confidence,
      filename: filename,
      image_preview: imagePreview,
    })
    return response.data
  } catch (err) {
    console.warn('selectFlowerApi error:', err)
    return null
  }
}

/**
 * Send a chat message about the current flower to backend-chatbot (port 8000).
 * @param {string} message
 * @returns {Promise<{ answer: string }>}
 */
export async function sendChatMessage(message) {
  const response = await chatbotApi.post('/chat', { message })
  return response.data
}

/**
 * Send a chat message with real-time ChatGPT-style token streaming.
 */
export async function streamChatMessage(message, onToken, onError, onDone) {
  try {
    const rawHost = import.meta.env.VITE_CHATBOT_API || import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_BASE_URL || ''
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
      throw new Error('Could not connect to Chatbot Service on port 8000. Please ensure backend-chatbot is running on port 8000.')
    }

    if (!response.ok) {
      const errText = await response.text()
      let errMsg = 'Failed to connect to streaming response.'
      if (response.status === 502 || response.status === 504) {
        errMsg = 'Chatbot Service is offline on port 8000. Please start backend-chatbot with: uvicorn app:app --port 8000'
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

/**
 * Translate text to a target language offline.
 */
export async function translateText(text, language) {
  const response = await chatbotApi.post('/translate', { text, language })
  return response.data
}

/**
 * Health check.
 */
export async function healthCheck() {
  const response = await chatbotApi.get('/health')
  return response.data
}

/**
 * Fetch search history records from MongoDB Atlas.
 */
export async function fetchHistory() {
  const response = await chatbotApi.get('/history')
  return response.data
}

/**
 * Save chat session history to MongoDB Atlas.
 */
export async function saveHistorySession(sessionData) {
  const response = await chatbotApi.post('/history/save', sessionData)
  return response.data
}

/**
 * Submit structured user feedback.
 */
export async function submitFeedbackApi(feedbackData) {
  const response = await chatbotApi.post('/api/analytics/feedback', feedbackData)
  return response.data
}

export default chatbotApi
