import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Star,
  AlertCircle,
  CheckCircle2,
  Send,
  ThumbsDown,
  Flower2,
} from 'lucide-react'
import { useApp } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import { submitFeedbackApi } from '../api/flowerApi'

const PREDEFINED_REASONS = [
  { id: 'Incorrect Information', label: 'Incorrect Information' },
  { id: 'Wrong Flower Identification', label: 'Wrong Flower Identification' },
  { id: 'Response Too Long', label: 'Response Too Long' },
  { id: 'Response Too Short', label: 'Response Too Short' },
  { id: 'Not Relevant', label: 'Not Relevant' },
  { id: 'Poor Explanation', label: 'Poor Explanation' },
  { id: 'Slow Response', label: 'Slow Response' },
  { id: 'Formatting Issue', label: 'Formatting Issue' },
  { id: 'Hallucinated Information', label: 'Hallucinated Info' },
  { id: 'Incomplete Answer', label: 'Incomplete Answer' },
  { id: 'Other', label: 'Other' },
]

const STAR_LABELS = ['', 'Poor', 'Fair', 'Good', 'Very Good', 'Excellent! ⭐']

export default function FeedbackModal() {
  const { state, closeFeedbackModal, showToast } = useApp()
  const { feedbackModalState, currentSessionId } = state
  const { user } = useAuth()
  const { isOpen, message, flowerName, prompt } = feedbackModalState || {}

  const [selectedReasons, setSelectedReasons] = useState([])
  const [rating, setRating] = useState(0)
  const [hoverRating, setHoverRating] = useState(0)
  const [customComment, setCustomComment] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!isOpen || !message) return null

  const handleToggleReason = (reasonId) => {
    if (selectedReasons.includes(reasonId)) {
      setSelectedReasons(selectedReasons.filter((r) => r !== reasonId))
    } else {
      setSelectedReasons([...selectedReasons, reasonId])
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSubmitting(true)

    const payload = {
      feedback_id: `fb_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
      session_id: currentSessionId || 'session_general',
      conversation_id: message.id || `conv_${Date.now()}`,
      user_id: user?.id || user?.google_id || 'anonymous',
      username: user?.name || 'Guest Botanist',
      email: user?.email || '',
      flower_name: flowerName || state.prediction?.flower || 'General Botany',
      user_prompt: prompt || 'User Query',
      ai_response: message.content || '',
      feedback_type: 'dislike',
      rating: rating,
      selected_reasons: selectedReasons,
      custom_comment: customComment,
      model_name: 'Flower_AI_Bot',
      request_status: 'success',
      feedback_status: 'new',
    }

    try {
      await submitFeedbackApi(payload)
      showToast('Thank you! Your feedback has been saved to the database.', 'success')
      closeFeedbackModal()
    } catch (err) {
      console.error('Failed to submit feedback to MongoDB:', err)
      showToast('Failed to save feedback. Please try again.', 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  const currentStarText = STAR_LABELS[hoverRating || rating] || ''

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[99999] flex items-center justify-center p-3 sm:p-5 bg-slate-900/60 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 12 }}
          transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="relative w-full max-w-lg rounded-3xl bg-white text-slate-800 shadow-2xl border border-slate-200/90 overflow-hidden flex flex-col max-h-[92vh]"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-white flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 shadow-sm flex-shrink-0">
                <ThumbsDown className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-display font-bold text-sm sm:text-base text-slate-900 tracking-tight flex items-center gap-2">
                  <span>Response Feedback</span>
                  <span className="text-[9px] font-extrabold tracking-wider uppercase px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 border border-rose-200">
                    AI Quality
                  </span>
                </h3>
                <p className="text-[11px] text-slate-500 font-medium">Help us improve Botanical AI response accuracy</p>
              </div>
            </div>
            <button
              onClick={closeFeedbackModal}
              className="p-1.5 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Form Content Body (Scrollable if needed, compact vertical gaps) */}
          <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto flex flex-col justify-between custom-scrollbar bg-white">
            <div className="p-5 space-y-4">
              {/* Context Box */}
              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200/90 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-100 border border-emerald-200 text-emerald-800 font-bold text-[11px]">
                    <Flower2 className="w-3 h-3 text-emerald-600" />
                    <span>Topic: {flowerName || state.prediction?.flower || 'General Botany'}</span>
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono font-semibold">Phi-3.5 Vision AI</span>
                </div>
                {prompt && (
                  <div className="text-slate-900 font-bold text-xs leading-snug">
                    <span className="text-emerald-700 font-extrabold mr-1">Query:</span>
                    "{prompt}"
                  </div>
                )}
                <div className="text-slate-600 text-[11px] line-clamp-2 leading-relaxed font-medium border-t border-slate-200/80 pt-1.5">
                  <span className="text-slate-800 font-bold mr-1">AI Output:</span>
                  {message.content}
                </div>
              </div>

              {/* Predefined Reasons Grid (Clean 2-Column Perfectly Aligned Cards) */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 text-rose-500" />
                    <span>What went wrong?</span>
                  </label>
                  <span className="text-[10px] text-slate-400 font-semibold">Select all that apply</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {PREDEFINED_REASONS.map((item) => {
                    const isSelected = selectedReasons.includes(item.id)
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => handleToggleReason(item.id)}
                        className={`px-3 py-2 rounded-xl text-left border transition-all duration-150 cursor-pointer flex items-center justify-between gap-2 ${
                          isSelected
                            ? 'bg-rose-50 border-rose-300 text-rose-900 shadow-sm font-bold'
                            : 'bg-slate-50 hover:bg-slate-100 border-slate-200 text-slate-700 font-medium'
                        }`}
                      >
                        <span className="text-xs font-semibold truncate">{item.label}</span>
                        {isSelected ? (
                          <CheckCircle2 className="w-4 h-4 text-rose-600 flex-shrink-0" />
                        ) : (
                          <span className="w-3.5 h-3.5 rounded-full border border-slate-300 flex-shrink-0" />
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Star Rating Section */}
              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200/90 space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                    <span>Rate response quality</span>
                  </label>
                  {currentStarText && (
                    <span className="text-xs font-bold text-amber-800 px-2 py-0.5 rounded-full bg-amber-100 border border-amber-300">
                      {currentStarText}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setRating(star)}
                      onMouseEnter={() => setHoverRating(star)}
                      onMouseLeave={() => setHoverRating(0)}
                      className="p-1 transition-transform hover:scale-125 focus:outline-none cursor-pointer"
                    >
                      <Star
                        className={`w-6 h-6 transition-colors ${
                          (hoverRating || rating) >= star
                            ? 'fill-amber-400 text-amber-500 drop-shadow-sm'
                            : 'text-slate-300 hover:text-amber-300'
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Comment Field */}
              <div className="space-y-1">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                  Additional Comments <span className="text-slate-400 font-normal">(Optional)</span>
                </label>
                <textarea
                  rows={2}
                  value={customComment}
                  onChange={(e) => setCustomComment(e.target.value)}
                  placeholder="Describe what information was missing or provide expected details..."
                  className="w-full p-2.5 rounded-xl border border-slate-300 bg-slate-50 text-slate-900 placeholder-slate-400 text-xs outline-none focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/20 transition-all resize-none font-medium"
                />
              </div>
            </div>

            {/* Fixed Bottom Action Bar (Guaranteed visible without scrolling) */}
            <div className="p-4 border-t border-slate-100 bg-white flex items-center gap-3 flex-shrink-0">
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs shadow-md hover:shadow-lg transition-all cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{isSubmitting ? 'Submitting...' : 'Submit Feedback'}</span>
              </button>

              <button
                type="button"
                onClick={closeFeedbackModal}
                className="py-3 px-4 rounded-xl border border-slate-300 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs transition-colors cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
