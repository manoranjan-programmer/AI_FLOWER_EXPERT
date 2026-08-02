import { useState } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism'
import {
  Copy,
  Check,
  Volume2,
  VolumeX,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
  Sparkles,
  User,
  Flower2,
  Share2,
  MessageSquare,
} from 'lucide-react'
import { useApp } from '../context/AppContext'

export default function ChatBubble({ message, isLastAssistant }) {
  const { state, speakText, setMessageReaction, openFeedbackModal, regenerateResponse, showToast } = useApp()
  const { speakingMessageId, messageReactions, theme } = state
  const [copied, setCopied] = useState(false)
  const [shared, setShared] = useState(false)

  const isUser = message.role === 'user'
  const isSpeaking = speakingMessageId === message.id
  const reaction = messageReactions[message.id]

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    showToast('Copied message to clipboard!', 'success')
    setTimeout(() => setCopied(false), 2000)
  }

  const handleShare = () => {
    if (navigator.share) {
      navigator
        .share({
          title: 'Flower AI Expert Answer',
          text: message.content,
          url: window.location.href,
        })
        .catch(() => {})
    } else {
      navigator.clipboard.writeText(message.content)
      setShared(true)
      showToast('Copied answer to share!', 'success')
      setTimeout(() => setShared(false), 2000)
    }
  }

  const syntaxStyle = theme === 'dark' ? vscDarkPlus : vs

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex gap-3 my-4 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {/* AI Avatar Icon */}
      {!isUser && (
        <div className="w-8 h-8 rounded-2xl flex items-center justify-center bg-gradient-to-tr from-emerald-500 to-teal-400 text-white shadow-md flex-shrink-0 mt-0.5 glow-effect">
          <Flower2 className="w-4 h-4 animate-spin-slow" />
        </div>
      )}

      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[92%] sm:max-w-[85%]`}>
        {/* Message Card */}
        <div
          className={`
            p-4 sm:p-5 rounded-3xl text-sm leading-relaxed shadow-sm transition-all duration-200
            ${
              isUser
                ? 'msg-user text-white'
                : 'glass-panel text-slate-900 dark:text-slate-100 border border-slate-200 dark:border-slate-800'
            }
          `}
          style={!isUser ? { background: 'var(--surface-2)' } : undefined}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap font-sans text-sm">{message.content}</p>
          ) : (
            <div className="prose-ai">
              {/* While streaming: render plain pre-wrap text to avoid expensive ReactMarkdown re-parse */}
              {message.isStreaming ? (
                <>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                    {message.content}
                  </p>
                  {/* Blinking cursor */}
                  <span className="inline-block w-[2.5px] h-4 ml-0.5 bg-emerald-500 animate-pulse rounded-sm" />
                </>
              ) : (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '')
                      return !inline && match ? (
                        <div className="relative group my-3 rounded-2xl overflow-hidden border border-slate-700/30 shadow-md">
                          <SyntaxHighlighter
                            style={syntaxStyle}
                            language={match[1]}
                            PreTag="div"
                            customStyle={{ margin: 0, borderRadius: '0.75rem', fontSize: '0.85rem', padding: '1rem' }}
                            {...props}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        </div>
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      )
                    },
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              )}
            </div>
          )}
        </div>

        {/* Message Action Toolbar & Timestamp */}
        {!isUser && !message.isStreaming && message.content && (
          <div className="flex items-center gap-1.5 mt-1.5 px-1 text-slate-400">
            {/* Copy Button */}
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-lg hover:bg-slate-500/15 transition-colors cursor-pointer"
              title="Copy Message"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            </button>

            {/* Read Aloud TTS */}
            <button
              onClick={() => speakText(message.content, message.id)}
              className={`p-1.5 rounded-lg transition-colors hover:bg-slate-500/15 cursor-pointer ${
                isSpeaking ? 'text-emerald-500 animate-pulse' : ''
              }`}
              title={isSpeaking ? 'Stop Speaking' : 'Read Aloud'}
            >
              {isSpeaking ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
            </button>

            {/* Like Feedback */}
            <button
              onClick={() => setMessageReaction(message.id, 'like')}
              className={`p-1.5 rounded-lg transition-colors hover:bg-slate-500/15 cursor-pointer ${
                reaction === 'like' ? 'text-emerald-500 fill-emerald-500/20' : ''
              }`}
              title="Good Response"
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>

            {/* Dislike Feedback */}
            <button
              onClick={() => setMessageReaction(message.id, 'dislike')}
              className={`p-1.5 rounded-lg transition-colors hover:bg-slate-500/15 cursor-pointer ${
                reaction === 'dislike' ? 'text-rose-500 fill-rose-500/20' : ''
              }`}
              title="Poor Response / Give Feedback"
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </button>

            {/* Detailed Feedback Form Button */}
            <button
              onClick={() => {
                const msgIdx = state.messages.findIndex((m) => m.id === message.id)
                let prevPrompt = ''
                if (msgIdx > 0 && state.messages[msgIdx - 1]?.role === 'user') {
                  prevPrompt = state.messages[msgIdx - 1].content
                }
                openFeedbackModal(message, prevPrompt)
              }}
              className="p-1.5 rounded-lg hover:bg-slate-500/15 transition-colors cursor-pointer text-slate-400 hover:text-emerald-400 flex items-center gap-1 text-[11px] font-semibold"
              title="Open Detailed Feedback Form"
            >
              <MessageSquare className="w-3.5 h-3.5 text-emerald-500" />
              <span className="hidden sm:inline">Feedback</span>
            </button>

            {/* Share Answer */}
            <button
              onClick={handleShare}
              className="p-1.5 rounded-lg hover:bg-slate-500/15 transition-colors cursor-pointer text-slate-400 hover:text-slate-200"
              title="Share Answer"
            >
              <Share2 className="w-3.5 h-3.5" />
            </button>

            {/* Regenerate (if last assistant response) */}
            {isLastAssistant && (
              <button
                onClick={regenerateResponse}
                className="p-1.5 rounded-lg hover:bg-slate-500/15 transition-colors cursor-pointer"
                title="Regenerate Answer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            )}

            {/* Timestamp */}
            {message.timestamp && (
              <span className="text-[10px] ml-2 text-slate-400">
                {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>
        )}

        {isUser && message.timestamp && (
          <span className="text-[10px] mt-1 text-slate-400 px-1">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>

      {/* User Avatar Icon */}
      {isUser && (
        <div className="w-8 h-8 rounded-2xl flex items-center justify-center bg-slate-700 text-white shadow-md flex-shrink-0 mt-0.5">
          <User className="w-4 h-4" />
        </div>
      )}
    </motion.div>
  )
}

