/**
 * AppContext.jsx
 * Central Global application state for Flower AI Expert.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  useRef,
} from 'react'
import { predictFlower, sendChatMessage, streamChatMessage, fetchHistory, saveHistorySession, submitFeedbackApi } from '../api/flowerApi'
import AuthContext from './AuthContext'

const loadFavorites = () => {
  try {
    const saved = localStorage.getItem('flower_ai_favorites')
    return saved ? JSON.parse(saved) : []
  } catch (e) {
    return []
  }
}

const loadHistory = () => {
  try {
    const saved = localStorage.getItem('flower_ai_history')
    return saved ? JSON.parse(saved) : []
  } catch (e) {
    return []
  }
}

const initialState = {
  theme: 'light',            // Pristine light mode default
  sidebarOpen: true,
  currentView: 'chat',       // 'chat' | 'landing' | 'identify' | 'favorites'
  language: localStorage.getItem('flower_ai_language') || 'en',

  activeModal: null,         // null | 'image-viewer' | 'shortcuts' | 'search'
  modalImageSrc: null,

  favorites: loadFavorites(),
  history: loadHistory(),
  currentSessionId: null,

  speakingMessageId: null,
  messageReactions: {},      // { [msgId]: 'like' | 'dislike' }
  feedbackModalState: { isOpen: false, message: null, flowerName: '', prompt: '' },

  imagePreview: null,
  prediction: null,
  uploadProgress: 0,

  messages: [],

  isPredicting: false,
  isChatLoading: false,
  error: null,
  toast: null,               // { id, text, type: 'info' | 'success' | 'warning' }
}

function reducer(state, action) {
  switch (action.type) {
    case 'SET_LANGUAGE':
      return { ...state, language: action.payload }

    case 'UPDATE_MESSAGE_CONTENT': {
      const { id, content } = action.payload
      const updatedMsgs = state.messages.map((msg) =>
        msg.id === id ? { ...msg, content, isStreaming: false } : msg
      )
      const activeSid = state.currentSessionId
      const updatedHistory = state.history.map((h) => {
        if (activeSid && (h.id === activeSid || h.session_id === activeSid)) {
          return { ...h, messages: updatedMsgs }
        }
        if (state.prediction && h.flower?.toLowerCase() === state.prediction.flower.toLowerCase()) {
          return { ...h, messages: updatedMsgs }
        }
        return h
      })
      try {
        localStorage.setItem('flower_ai_history', JSON.stringify(updatedHistory))
      } catch (e) {}
      return {
        ...state,
        messages: updatedMsgs,
        history: updatedHistory,
      }
    }

    case 'RESET_CHAT':
      return {
        ...state,
        imagePreview: null,
        prediction: null,
        currentSessionId: null,
        messages: [],
        error: null,
        uploadProgress: 0,
      }

    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarOpen: !state.sidebarOpen }

    case 'SET_SIDEBAR_OPEN':
      return { ...state, sidebarOpen: action.payload }

    case 'SET_THEME':
      return { ...state, theme: action.payload }

    case 'TOGGLE_THEME':
      return { ...state, theme: state.theme === 'dark' ? 'light' : 'dark' }

    case 'SET_VIEW':
      return { ...state, currentView: action.payload }

    case 'SET_ACTIVE_MODAL':
      return { ...state, activeModal: action.payload }

    case 'OPEN_IMAGE_MODAL':
      return { ...state, activeModal: 'image-viewer', modalImageSrc: action.payload }

    case 'SET_SPEAKING_ID':
      return { ...state, speakingMessageId: action.payload }

    case 'SET_MESSAGE_REACTION': {
      const { id, type } = action.payload
      const current = state.messageReactions[id]
      const updated = { ...state.messageReactions }
      if (current === type) {
        delete updated[id]
      } else {
        updated[id] = type
      }
      return { ...state, messageReactions: updated }
    }

    case 'SHOW_TOAST':
      return { ...state, toast: { id: Date.now(), text: action.payload.text, type: action.payload.type || 'info' } }

    case 'CLEAR_TOAST':
      return { ...state, toast: null }

    case 'TOGGLE_FAVORITE': {
      const plant = action.payload
      const exists = state.favorites.some((item) => item.flower?.toLowerCase() === plant.flower?.toLowerCase())
      const updated = exists
        ? state.favorites.filter((item) => item.flower?.toLowerCase() !== plant.flower?.toLowerCase())
        : [{ ...plant, savedAt: new Date().toISOString() }, ...state.favorites]
      try {
        localStorage.setItem('flower_ai_favorites', JSON.stringify(updated))
      } catch (e) {}
      return { ...state, favorites: updated }
    }

    case 'SET_IMAGE_PREVIEW':
      return { ...state, imagePreview: action.payload }

    case 'SET_UPLOAD_PROGRESS':
      return { ...state, uploadProgress: action.payload }

    case 'PREDICT_START':
      return {
        ...state,
        isPredicting: true,
        error: null,
        prediction: null,
        uploadProgress: 0,
      }

    case 'SET_HISTORY_FROM_SERVER': {
      const serverItems = action.payload || []
      const merged = serverItems.map((item) => ({
        id: item.session_id || item.id || Date.now(),
        flower: item.flower,
        confidence: item.confidence,
        summary: item.summary,
        card: item.card || {},
        imagePreview: item.image_preview || item.imagePreview || null,
        messages: item.messages || [],
        timestamp: item.searched_at || item.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        date: item.timestamp ? new Date(item.timestamp).toLocaleDateString() : new Date().toLocaleDateString(),
      }))
      return { ...state, history: merged }
    }

    case 'LOAD_SESSION': {
      const item = action.payload
      const isNamedFlower = item.flower && item.flower !== 'AI Botanical Chat' && item.flower !== 'General AI Chat'
      const restoredPrediction = isNamedFlower ? {
        flower: item.flower,
        confidence: item.confidence || 98.5,
        summary: item.summary || '',
        card: item.card || {},
      } : null

      const initialMessage = restoredPrediction ? {
        id: Date.now(),
        role: 'assistant',
        content: `Identified as **${restoredPrediction.flower}** (${restoredPrediction.confidence}% accuracy) 🌸\n\n${restoredPrediction.summary || ''}\n\nAsk me anything about its sunlight, watering schedule, or soil care!`,
        timestamp: new Date().toISOString(),
      } : null

      const restoredMessages = item.messages && item.messages.length > 0
        ? item.messages
        : (initialMessage ? [initialMessage] : [])

      return {
        ...state,
        prediction: restoredPrediction,
        currentSessionId: item.session_id || item.id,
        imagePreview: item.imagePreview || item.image_preview || null,
        messages: restoredMessages,
        currentView: 'chat',
      }
    }

    case 'PREDICT_SUCCESS': {
      const initialAssistantMessage = {
        id: Date.now(),
        role: 'assistant',
        content: `Identified as **${action.payload.flower}** (${action.payload.confidence}% accuracy) 🌸\n\n${action.payload.summary}\n\nAsk me anything about its sunlight, watering schedule, or soil care!`,
        timestamp: new Date().toISOString(),
      }
      const initialMessages = [initialAssistantMessage]

      const sessionId = action.payload.session_id || `session_${action.payload.flower.toLowerCase().replace(/\s+/g, '_')}_${Date.now()}`
      const historyItem = {
        id: sessionId,
        session_id: sessionId,
        flower: action.payload.flower,
        confidence: action.payload.confidence,
        summary: action.payload.summary,
        card: action.payload.card,
        imagePreview: state.imagePreview,
        messages: initialMessages,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        date: new Date().toLocaleDateString(),
      }
      const newHistory = [historyItem, ...state.history.filter((h) => h.id !== sessionId)]
      try {
        localStorage.setItem('flower_ai_history', JSON.stringify(newHistory))
      } catch (e) {}

      return {
        ...state,
        isPredicting: false,
        prediction: action.payload,
        currentSessionId: sessionId,
        history: newHistory,
        messages: initialMessages,
        currentView: 'chat',
        uploadProgress: 100,
      }
    }

    case 'PREDICT_ERROR':
      return {
        ...state,
        isPredicting: false,
        error: action.payload,
        uploadProgress: 0,
      }

    case 'ADD_MESSAGE': {
      const newMsg = {
        id: action.payload.id || Date.now() + Math.random(),
        ...action.payload,
        timestamp: new Date().toISOString(),
      }
      const updatedMessages = [...state.messages, newMsg]

      const activeSid = state.currentSessionId || `session_chat_${Date.now()}`
      const flowerName = state.prediction?.flower || 'AI Botanical Chat'

      const existingHistoryIndex = state.history.findIndex(
        (h) => h.id === activeSid || h.session_id === activeSid
      )

      let updatedHistory
      if (existingHistoryIndex >= 0) {
        updatedHistory = state.history.map((h, i) =>
          i === existingHistoryIndex ? { ...h, messages: updatedMessages } : h
        )
      } else {
        const historyItem = {
          id: activeSid,
          session_id: activeSid,
          flower: flowerName,
          confidence: state.prediction?.confidence || 99.0,
          summary: state.prediction?.summary || 'Interactive AI Botanical Conversation',
          card: state.prediction?.card || {},
          imagePreview: state.imagePreview || null,
          messages: updatedMessages,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          date: new Date().toLocaleDateString(),
        }
        updatedHistory = [historyItem, ...state.history]
      }

      try {
        localStorage.setItem('flower_ai_history', JSON.stringify(updatedHistory))
      } catch (e) {}

      return {
        ...state,
        currentSessionId: activeSid,
        messages: updatedMessages,
        history: updatedHistory,
      }
    }

    case 'DELETE_LAST_ASSISTANT_MESSAGE': {
      const lastIndex = state.messages.findLastIndex((m) => m.role === 'assistant')
      if (lastIndex === -1) return state
      const updated = [...state.messages]
      updated.splice(lastIndex, 1)
      return { ...state, messages: updated }
    }

    case 'APPEND_TOKEN': {
      const { id, token } = action.payload
      return {
        ...state,
        isChatLoading: false,
        messages: state.messages.map((msg) =>
          msg.id === id
            ? { ...msg, content: msg.content + token, isStreaming: true }
            : msg
        ),
      }
    }

    // Batch-flush accumulated tokens in one shot (RAF-batched)
    case 'FLUSH_TOKENS': {
      const { id, text } = action.payload
      const updatedMsgs = state.messages.map((msg) =>
        msg.id === id
          ? { ...msg, content: msg.content + text, isStreaming: true }
          : msg
      )
      const activeSid = state.currentSessionId
      const updatedHistory = state.history.map((h) => {
        if (activeSid && (h.id === activeSid || h.session_id === activeSid)) {
          return { ...h, messages: updatedMsgs }
        }
        if (state.prediction && h.flower?.toLowerCase() === state.prediction.flower.toLowerCase()) {
          return { ...h, messages: updatedMsgs }
        }
        return h
      })
      return {
        ...state,
        isChatLoading: false,
        messages: updatedMsgs,
        history: updatedHistory,
      }
    }

    case 'FINISH_STREAMING': {
      const { id } = action.payload
      const updatedMsgs = state.messages.map((msg) =>
        msg.id === id
          ? { ...msg, isStreaming: false }
          : msg
      )
      const activeSid = state.currentSessionId
      const updatedHistory = state.history.map((h) => {
        if (activeSid && (h.id === activeSid || h.session_id === activeSid)) {
          return { ...h, messages: updatedMsgs }
        }
        if (state.prediction && h.flower?.toLowerCase() === state.prediction.flower.toLowerCase()) {
          return { ...h, messages: updatedMsgs }
        }
        return h
      })
      try {
        localStorage.setItem('flower_ai_history', JSON.stringify(updatedHistory))
      } catch (e) {}
      return {
        ...state,
        isChatLoading: false,
        messages: updatedMsgs,
        history: updatedHistory,
      }
    }

    case 'OPEN_FEEDBACK_MODAL':
      return {
        ...state,
        feedbackModalState: {
          isOpen: true,
          message: action.payload.message,
          flowerName: action.payload.flowerName || state.prediction?.flower || 'General Botany',
          prompt: action.payload.prompt || '',
        },
      }

    case 'CLOSE_FEEDBACK_MODAL':
      return {
        ...state,
        feedbackModalState: { isOpen: false, message: null, flowerName: '', prompt: '' },
      }

    case 'CHAT_LOADING':
      return { ...state, isChatLoading: action.payload }

    case 'CLEAR_ERROR':
      return { ...state, error: null }

    case 'SET_ERROR':
      return { ...state, error: action.payload }

    default:
      return state
  }
}

const AppContext = createContext(null)

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  const authCtx = useContext(AuthContext)

  // Sync theme class on <html>
  useEffect(() => {
    if (state.theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [state.theme])

  // Toast auto dismiss
  useEffect(() => {
    if (state.toast) {
      const timer = setTimeout(() => dispatch({ type: 'CLEAR_TOAST' }), 3000)
      return () => clearTimeout(timer)
    }
  }, [state.toast])

  // Toast Helper
  const showToast = useCallback((text, type = 'info') => {
    dispatch({ type: 'SHOW_TOAST', payload: { text, type } })
  }, [])

  // Speech Synthesis
  const speakText = useCallback((text, messageId) => {
    if (!('speechSynthesis' in window)) {
      showToast('Speech Synthesis is not supported in this browser.', 'warning')
      return
    }

    if (state.speakingMessageId === messageId) {
      window.speechSynthesis.cancel()
      dispatch({ type: 'SET_SPEAKING_ID', payload: null })
      return
    }

    window.speechSynthesis.cancel()
    const cleanText = text.replace(/[*_#`~[\]()]/g, '').replace(/<[^>]*>/g, '').trim()

    const utterance = new SpeechSynthesisUtterance(cleanText)
    utterance.rate = 1.0
    utterance.pitch = 1.0

    utterance.onend = () => dispatch({ type: 'SET_SPEAKING_ID', payload: null })
    utterance.onerror = () => dispatch({ type: 'SET_SPEAKING_ID', payload: null })

    dispatch({ type: 'SET_SPEAKING_ID', payload: messageId })
    window.speechSynthesis.speak(utterance)
  }, [state.speakingMessageId, showToast])

  const toggleTheme = useCallback(() => {
    dispatch({ type: 'TOGGLE_THEME' })
  }, [])

  const setView = useCallback((viewName) => {
    dispatch({ type: 'SET_VIEW', payload: viewName })
  }, [])

  const setActiveModal = useCallback((modalName) => {
    dispatch({ type: 'SET_ACTIVE_MODAL', payload: modalName })
  }, [])

  const openImageModal = useCallback((src) => {
    dispatch({ type: 'OPEN_IMAGE_MODAL', payload: src })
  }, [])

  const toggleFavorite = useCallback((plantData) => {
    dispatch({ type: 'TOGGLE_FAVORITE', payload: plantData })
    const isFav = state.favorites.some((item) => item.flower?.toLowerCase() === plantData.flower?.toLowerCase())
    showToast(isFav ? `Removed ${plantData.flower} from favorites` : `Saved ${plantData.flower} to favorites! ❤️`, 'success')
  }, [state.favorites, showToast])

  const isFavorite = useCallback((flowerName) => {
    if (!flowerName) return false
    return state.favorites.some((item) => item.flower?.toLowerCase() === flowerName.toLowerCase())
  }, [state.favorites])

  const openFeedbackModal = useCallback((message, prompt) => {
    dispatch({
      type: 'OPEN_FEEDBACK_MODAL',
      payload: {
        message,
        prompt,
        flowerName: state.prediction?.flower || 'General Botany',
      },
    })
  }, [state.prediction])

  const closeFeedbackModal = useCallback(() => {
    dispatch({ type: 'CLOSE_FEEDBACK_MODAL' })
  }, [])

  const setMessageReaction = useCallback((id, type) => {
    dispatch({ type: 'SET_MESSAGE_REACTION', payload: { id, type } })

    const targetMsg = state.messages.find((m) => m.id === id)
    const msgIdx = state.messages.findIndex((m) => m.id === id)
    let prevPrompt = ''
    if (msgIdx > 0 && state.messages[msgIdx - 1]?.role === 'user') {
      prevPrompt = state.messages[msgIdx - 1].content
    }

    if (targetMsg) {
      const authUser = authCtx?.user
      submitFeedbackApi({
        session_id: state.currentSessionId || 'session_general',
        conversation_id: id || `conv_${Date.now()}`,
        user_prompt: prevPrompt || 'Botanical Question',
        ai_response: targetMsg.content || '',
        flower_name: state.prediction?.flower || 'General Botany',
        feedback_type: type,
        rating: type === 'like' ? 5 : 1,
        selected_reasons: [],
        custom_comment: '',
        model_name: 'Flower_AI_Bot',
        request_status: 'success',
        user_id: authUser?.id || authUser?.google_id || 'anonymous',
        username: authUser?.name || 'Guest Botanist',
        email: authUser?.email || '',
      }).catch((err) => console.warn('Background feedback save warning:', err))
    }

    if (type === 'like') {
      showToast('Thank you for your feedback! 👍', 'success')
    } else {
      showToast('Feedback recorded 👎 - Tell us how we can improve', 'info')
      openFeedbackModal(targetMsg, prevPrompt)
    }
  }, [state.messages, state.currentSessionId, state.prediction, showToast, openFeedbackModal])

  const goToLanding = useCallback(() => {
    dispatch({ type: 'SET_VIEW', payload: 'landing' })
  }, [])

  const handleImageUpload = useCallback(async (file) => {
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => dispatch({ type: 'SET_IMAGE_PREVIEW', payload: e.target.result })
    reader.readAsDataURL(file)

    dispatch({ type: 'PREDICT_START' })
    const startTime = Date.now()

    try {
      // Simulate smooth progress ticks for scanning effect
      dispatch({ type: 'SET_UPLOAD_PROGRESS', payload: 25 })
      const resultPromise = predictFlower(file, (pct) => {
        const adjustedPct = Math.max(25, Math.min(90, Math.round(pct * 0.9)))
        dispatch({ type: 'SET_UPLOAD_PROGRESS', payload: adjustedPct })
      })

      const result = await resultPromise
      dispatch({ type: 'SET_UPLOAD_PROGRESS', payload: 95 })

      // Guarantee minimum 2.2s duration so the scanner animation plays smoothly
      const elapsed = Date.now() - startTime
      const minScanTime = 2200
      if (elapsed < minScanTime) {
        await new Promise((resolve) => setTimeout(resolve, minScanTime - elapsed))
      }

      dispatch({ type: 'PREDICT_SUCCESS', payload: result })
      showToast(`Successfully identified as ${result.flower}! ✨`, 'success')
    } catch (err) {
      dispatch({ type: 'PREDICT_ERROR', payload: err.message })
      showToast(`Upload failed: ${err.message}`, 'warning')
    }
  }, [showToast])

  // 16ms timer-based token batcher – flushes accumulated tokens continuously (~60fps)
  // without pausing when switching tabs or waiting on browser paint frames.
  const _tokenBuffer = useRef('')
  const _flushTimer  = useRef(null)
  const _flushId     = useRef(null)

  const _scheduleFlush = useCallback((botMsgId) => {
    if (_flushTimer.current !== null) return   // already scheduled
    _flushTimer.current = setTimeout(() => {
      const accumulated = _tokenBuffer.current
      _tokenBuffer.current = ''
      _flushTimer.current = null
      if (accumulated) {
        dispatch({ type: 'FLUSH_TOKENS', payload: { id: botMsgId, text: accumulated } })
      }
    }, 16)
  }, [])

  const sendMessage = useCallback(async (text) => {
    if (!text.trim()) return

    const userMsgId = Date.now()
    const botMsgId = Date.now() + 1

    // Reset batcher state for new message
    _tokenBuffer.current = ''
    _flushId.current = botMsgId
    if (_flushTimer.current !== null) {
      clearTimeout(_flushTimer.current)
      _flushTimer.current = null
    }

    dispatch({ type: 'ADD_MESSAGE', payload: { id: userMsgId, role: 'user', content: text } })
    dispatch({ type: 'CHAT_LOADING', payload: true })
    dispatch({ type: 'CLEAR_ERROR' })

    // Insert assistant message placeholder for streaming
    dispatch({
      type: 'ADD_MESSAGE',
      payload: { id: botMsgId, role: 'assistant', content: '', isStreaming: true },
    })

    await streamChatMessage(
      text,
      (token) => {
        // Buffer the token and schedule a flush
        _tokenBuffer.current += token
        _scheduleFlush(botMsgId)
      },
      (err) => {
        // Flush any pending tokens first, then show error
        if (_tokenBuffer.current) {
          dispatch({ type: 'FLUSH_TOKENS', payload: { id: botMsgId, text: _tokenBuffer.current } })
          _tokenBuffer.current = ''
        }
        if (_flushTimer.current !== null) {
          clearTimeout(_flushTimer.current)
          _flushTimer.current = null
        }
        dispatch({ type: 'SET_ERROR', payload: err.message })
        dispatch({
          type: 'FLUSH_TOKENS',
          payload: {
            id: botMsgId,
            text: `\n\n*Error generating response: ${err.message}*`,
          },
        })
        dispatch({ type: 'FINISH_STREAMING', payload: { id: botMsgId } })
      },
      () => {
        // Final flush before marking done
        if (_tokenBuffer.current) {
          dispatch({ type: 'FLUSH_TOKENS', payload: { id: botMsgId, text: _tokenBuffer.current } })
          _tokenBuffer.current = ''
        }
        if (_flushTimer.current !== null) {
          clearTimeout(_flushTimer.current)
          _flushTimer.current = null
        }
        dispatch({ type: 'FINISH_STREAMING', payload: { id: botMsgId } })
      }
    )
  }, [_scheduleFlush])

  const regenerateResponse = useCallback(async () => {
    const lastUserMessage = [...state.messages].reverse().find((m) => m.role === 'user')
    if (!lastUserMessage) return

    // Reset batcher
    _tokenBuffer.current = ''
    if (_flushTimer.current !== null) {
      clearTimeout(_flushTimer.current)
      _flushTimer.current = null
    }

    dispatch({ type: 'DELETE_LAST_ASSISTANT_MESSAGE' })
    const botMsgId = Date.now()
    _flushId.current = botMsgId
    dispatch({ type: 'CHAT_LOADING', payload: true })

    dispatch({
      type: 'ADD_MESSAGE',
      payload: { id: botMsgId, role: 'assistant', content: '', isStreaming: true },
    })

    await streamChatMessage(
      lastUserMessage.content,
      (token) => {
        _tokenBuffer.current += token
        _scheduleFlush(botMsgId)
      },
      (err) => {
        if (_tokenBuffer.current) {
          dispatch({ type: 'FLUSH_TOKENS', payload: { id: botMsgId, text: _tokenBuffer.current } })
          _tokenBuffer.current = ''
        }
        if (_flushTimer.current !== null) {
          clearTimeout(_flushTimer.current)
          _flushTimer.current = null
        }
        dispatch({ type: 'SET_ERROR', payload: err.message })
        dispatch({ type: 'FINISH_STREAMING', payload: { id: botMsgId } })
      },
      () => {
        if (_tokenBuffer.current) {
          dispatch({ type: 'FLUSH_TOKENS', payload: { id: botMsgId, text: _tokenBuffer.current } })
          _tokenBuffer.current = ''
        }
        if (_flushTimer.current !== null) {
          clearTimeout(_flushTimer.current)
          _flushTimer.current = null
        }
        dispatch({ type: 'FINISH_STREAMING', payload: { id: botMsgId } })
      }
    )
  }, [state.messages, _scheduleFlush])

  // Load search history from MongoDB Atlas on mount
  useEffect(() => {
    fetchHistory()
      .then((data) => {
        if (data && data.history && data.history.length > 0) {
          dispatch({ type: 'SET_HISTORY_FROM_SERVER', payload: data.history })
        }
      })
      .catch(() => {})
  }, [])

  // Sync active chat session messages to MongoDB Atlas (ONLY after streaming finishes, avoiding network congestion during streaming)
  useEffect(() => {
    if (state.messages.length > 0 && !state.isChatLoading) {
      const isAnyStreaming = state.messages.some((m) => m.isStreaming)
      if (isAnyStreaming) return // Do NOT spam backend during active streaming!

      const activeSession = state.history.find(
        (h) => h.id === state.currentSessionId || h.session_id === state.currentSessionId
      )
      const flowerName = state.prediction?.flower || activeSession?.flower || 'AI Botanical Chat'
      const sid = state.currentSessionId || activeSession?.session_id || `session_chat_${Date.now()}`

      saveHistorySession({
        session_id: sid,
        flower: flowerName,
        confidence: state.prediction?.confidence || activeSession?.confidence || 99.0,
        summary: state.prediction?.summary || activeSession?.summary || 'Interactive AI Botanical Conversation',
        card: state.prediction?.card || activeSession?.card || {},
        image_preview: state.imagePreview || activeSession?.imagePreview || '',
        messages: state.messages,
      }).catch(() => {})
    }
  }, [state.currentSessionId, state.prediction, state.messages, state.imagePreview, state.isChatLoading, state.history])

  const loadSession = useCallback((sessionItem) => {
    if (!sessionItem) return
    dispatch({ type: 'LOAD_SESSION', payload: sessionItem })
    showToast(`Loaded conversation for ${sessionItem.flower || 'plant'} 🌸`, 'info')
  }, [showToast])

  const setLanguage = useCallback((langCode) => {
    dispatch({ type: 'SET_LANGUAGE', payload: langCode })
    try {
      localStorage.setItem('flower_ai_language', langCode)
    } catch (e) {}
  }, [])

  const translateLastAnswer = useCallback(async (targetLang) => {
    const lastAssistantMsg = [...state.messages].reverse().find((m) => m.role === 'assistant')
    if (!lastAssistantMsg || !lastAssistantMsg.content) return
    const langCode = targetLang || state.language
    if (langCode === 'en') return

    try {
      showToast(`Translating response... 🌐`, 'info')
      const data = await translateText(lastAssistantMsg.content, langCode)
      if (data && data.translated) {
        dispatch({
          type: 'UPDATE_MESSAGE_CONTENT',
          payload: { id: lastAssistantMsg.id, content: data.translated },
        })
        showToast(`Response translated! ✨`, 'success')
      }
    } catch (err) {
      showToast(`Translation failed: ${err.message}`, 'warning')
    }
  }, [state.messages, state.language, showToast])

  const clearError = useCallback(() => dispatch({ type: 'CLEAR_ERROR' }), [])
  const resetChat = useCallback(() => {
    dispatch({ type: 'RESET_CHAT' })
    dispatch({ type: 'SET_VIEW', payload: 'chat' })
    showToast('New Chat Session started', 'info')
  }, [showToast])

  const toggleSidebar = useCallback(() => dispatch({ type: 'TOGGLE_SIDEBAR' }), [])

  const value = {
    state,
    dispatch,
    toggleTheme,
    setLanguage,
    translateLastAnswer,
    setView,
    setActiveModal,
    openImageModal,
    toggleFavorite,
    isFavorite,
    speakText,
    setMessageReaction,
    openFeedbackModal,
    closeFeedbackModal,
    showToast,
    goToLanding,
    handleImageUpload,
    sendMessage,
    regenerateResponse,
    clearError,
    resetChat,
    toggleSidebar,
    loadSession,
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>')
  return ctx
}

export default AppContext
