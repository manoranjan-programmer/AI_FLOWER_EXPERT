import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send,
  Paperclip,
  Mic,
  MicOff,
  Sparkles,
  RefreshCw,
  Image as ImageIcon,
  X,
  Bot,
  AlertTriangle,
  CornerDownLeft,
} from 'lucide-react'
import { useApp } from '../context/AppContext'
import ChatBubble from './ChatBubble'
import SuggestedQuestions from './SuggestedQuestions'

export default function ChatWindow() {
  const { state, sendMessage, handleImageUpload, resetChat, clearError, showToast } = useApp()
  const { messages, isChatLoading, error, imagePreview, prediction } = state

  const [input, setInput] = useState('')
  const [isListening, setIsListening] = useState(false)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  // Auto-scroll: immediate for new distinct messages, debounced during streaming
  const scrollTimerRef = useRef(null)

  const scrollToBottom = useCallback((immediate = false) => {
    if (immediate) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
      return
    }
    if (scrollTimerRef.current) return
    scrollTimerRef.current = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
      scrollTimerRef.current = null
    }, 120)
  }, [])

  const prevMsgCountRef = useRef(0)
  useEffect(() => {
    const isNewMessage = messages.length > prevMsgCountRef.current
    prevMsgCountRef.current = messages.length
    if (isNewMessage || isChatLoading) {
      scrollToBottom(true)
    } else {
      scrollToBottom(false)
    }
  }, [messages, isChatLoading, scrollToBottom])

  // Speech Recognition (Voice Input)
  const toggleVoiceInput = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      showToast('Speech Recognition is not supported in your browser.', 'warning')
      return
    }

    if (isListening) {
      setIsListening(false)
      return
    }

    try {
      const recognition = new SpeechRecognition()
      recognition.continuous = false
      recognition.interimResults = false
      recognition.lang = 'en-US'

      recognition.onstart = () => {
        setIsListening(true)
        showToast('Listening... Speak now 🎙️', 'info')
      }

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        setInput((prev) => (prev ? `${prev} ${transcript}` : transcript))
        setIsListening(false)
      }

      recognition.onerror = (err) => {
        setIsListening(false)
        showToast(`Voice input error: ${err.error}`, 'warning')
      }

      recognition.onend = () => {
        setIsListening(false)
      }

      recognition.start()
    } catch (e) {
      setIsListening(false)
      showToast('Could not initialize microphone.', 'warning')
    }
  }

  // Image Clipboard Paste Support
  const handlePaste = (e) => {
    const items = e.clipboardData?.items
    if (!items) return

    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const file = items[i].getAsFile()
        if (file) {
          e.preventDefault()
          handleImageUpload(file)
          showToast('Pasted image uploaded for classification! 🌸', 'success')
          break
        }
      }
    }
  }

  const handleSubmit = (e) => {
    e?.preventDefault()
    if (!input.trim() || isChatLoading) return
    sendMessage(input.trim())
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  // Auto-resize textarea height
  const handleInputChange = (e) => {
    setInput(e.target.value)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`
    }
  }

  const lastAssistantIndex = messages.findLastIndex((m) => m.role === 'assistant')

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden relative" style={{ background: 'var(--surface)' }}>
      {/* ERROR BANNER */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex items-center justify-between px-4 py-2.5 bg-amber-500/15 border-b border-amber-500/30 text-amber-500 text-xs font-semibold z-20"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
            <button onClick={clearError} className="p-1 hover:bg-amber-500/20 rounded-lg cursor-pointer">
              <X className="w-3.5 h-3.5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* MESSAGES STREAM OR SUGGESTIONS */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 max-w-5xl w-full mx-auto space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <SuggestedQuestions />
          </div>
        ) : (
          messages.map((msg, index) => (
            <ChatBubble
              key={msg.id || index}
              message={msg}
              isLastAssistant={index === lastAssistantIndex}
            />
          ))
        )}

        {/* TYPING INDICATOR LOADING STATE */}
        {isChatLoading && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3 py-2 text-xs font-semibold"
            style={{ color: 'var(--text-muted)' }}
          >
            <div className="w-8 h-8 rounded-2xl flex items-center justify-center bg-emerald-500/20 text-emerald-500 font-bold shadow-sm glow-effect">
              <Bot className="w-4 h-4 animate-bounce" />
            </div>
            <div className="flex items-center gap-2 px-4 py-2.5 rounded-2xl border glass-panel">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              <span>AI Botanist is formulating answer...</span>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* BOTTOM FLOATING CHAT INPUT BAR */}
      <div className="p-4 z-20 glass-header border-t sticky bottom-0" style={{ borderColor: 'var(--border)' }}>
        <div className="max-w-4xl mx-auto w-full space-y-2">
          {/* Active Flower Context Badge if Prediction exists */}
          {prediction && (
            <div className="flex items-center justify-between px-3.5 py-1.5 rounded-2xl text-xs border glass-panel" style={{ background: 'var(--surface-3)', borderColor: 'var(--border)' }}>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span className="font-semibold text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                  Active Context: <strong style={{ color: 'var(--text-primary)' }}>{prediction.flower}</strong> ({prediction.confidence}% confidence)
                </span>
              </div>
              <button
                onClick={resetChat}
                className="text-[10px] text-emerald-500 hover:underline font-bold cursor-pointer"
              >
                Clear context
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit} className="relative flex items-center">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) handleImageUpload(file)
              }}
            />

            {/* Floating input container */}
            <div
              className="flex-1 flex items-center gap-2 p-2 rounded-3xl border shadow-xl transition-all duration-200 glass-panel"
              style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}
            >
              {/* Image Upload Button */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="p-2.5 rounded-2xl hover:bg-slate-500/10 transition-colors text-slate-400 hover:text-emerald-500 flex-shrink-0 cursor-pointer"
                title="Upload or Paste Flower Image"
              >
                <Paperclip className="w-4 h-4" />
              </button>

              {/* Textarea Input */}
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                placeholder="Ask Flower AI anything... (or paste flower image)"
                rows={1}
                className="w-full text-sm outline-none resize-none bg-transparent py-1.5 px-1 max-h-44"
                style={{ color: 'var(--text-primary)' }}
              />

              {/* Voice Recognition Button */}
              <button
                type="button"
                onClick={toggleVoiceInput}
                className={`p-2.5 rounded-2xl transition-all flex-shrink-0 cursor-pointer ${
                  isListening
                    ? 'bg-rose-500 text-white animate-pulse shadow-md'
                    : 'text-slate-400 hover:text-emerald-500 hover:bg-slate-500/10'
                }`}
                title={isListening ? 'Stop Listening' : 'Voice Input'}
              >
                {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>

              {/* Submit / Send Button */}
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                type="submit"
                disabled={!input.trim() || isChatLoading}
                className="p-2.5 rounded-2xl text-white shadow-md disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0 cursor-pointer"
                style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}
                title="Send Message"
              >
                <Send className="w-4 h-4" />
              </motion.button>
            </div>
          </form>

          {/* Footer note */}
          <div className="flex items-center justify-between px-2 text-[10px]" style={{ color: 'var(--text-muted)' }}>
            <span>Press <kbd className="px-1 py-0.5 rounded border" style={{ borderColor: 'var(--border)' }}>Enter</kbd> to send, <kbd className="px-1 py-0.5 rounded border" style={{ borderColor: 'var(--border)' }}>Shift + Enter</kbd> for line break</span>
            <span className="hidden sm:inline">Powered by Phi-3.5 Vision AI & EfficientNet</span>
          </div>
        </div>
      </div>
    </div>
  )
}

