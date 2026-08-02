import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Image as ImageIcon, MessageSquare, SlidersHorizontal, Sparkles } from 'lucide-react'
import { useApp } from '../context/AppContext'
import ImageUpload from '../components/ImageUpload'
import PredictionCard from '../components/PredictionCard'
import ChatWindow from '../components/ChatWindow'

export default function ChatPage() {
  const { state } = useApp()
  const { prediction, isPredicting } = state
  const [mobileTab, setMobileTab] = useState('chat')

  return (
    <div className="flex-1 flex flex-col overflow-hidden h-full">
      {/* Mobile Navigation Tabs */}
      <div className="flex lg:hidden flex-shrink-0 glass-header border-b z-20" style={{ borderColor: 'var(--border)' }}>
        {[
          { key: 'image', icon: ImageIcon, label: 'Flower Inspector' },
          { key: 'chat', icon: MessageSquare, label: 'AI Chat' },
        ].map(({ key, icon: IconComp, label }) => (
          <button
            key={key}
            onClick={() => setMobileTab(key)}
            className="flex-1 flex items-center justify-center gap-2 py-3 text-xs font-bold transition-colors cursor-pointer"
            style={{
              color: mobileTab === key ? 'var(--accent)' : 'var(--text-secondary)',
              borderBottom: mobileTab === key ? '2.5px solid var(--accent)' : '2.5px solid transparent',
            }}
          >
            <IconComp className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Main Workspace Layout */}
      <div className="flex-1 flex overflow-hidden min-h-0 relative">
        {/* LEFT FLOWER INSPECTOR SIDEBAR PANEL */}
        <aside
          className={`
            flex-shrink-0 w-full lg:w-80 xl:w-96 flex flex-col overflow-y-auto border-r
            ${mobileTab === 'image' ? 'flex' : 'hidden lg:flex'}
          `}
          style={{
            borderColor: 'var(--border)',
            background: 'var(--surface-2)',
          }}
        >
          {/* Upload Area */}
          <div className="p-4 border-b" style={{ borderColor: 'var(--border)' }}>
            <p className="text-[10px] font-bold uppercase tracking-wider mb-3 flex items-center justify-between" style={{ color: 'var(--text-muted)' }}>
              <span>Flower Image Classification</span>
              <span className="text-emerald-500 font-mono">ResNet-50</span>
            </p>
            <ImageUpload />
          </div>

          {/* Species Prediction & Care Cards */}
          <div className="p-4 flex-1">
            <AnimatePresence mode="wait">
              {isPredicting && (
                <motion.div
                  key="skeleton"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-3 p-2"
                >
                  {[85, 65, 75, 55, 90].map((w, i) => (
                    <div
                      key={i}
                      className="h-4 rounded-xl animate-shimmer"
                      style={{
                        width: `${w}%`,
                      }}
                    />
                  ))}
                </motion.div>
              )}

              {prediction && !isPredicting && (
                <motion.div
                  key="card"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                >
                  <PredictionCard prediction={prediction} />
                </motion.div>
              )}

              {!prediction && !isPredicting && (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-col items-center justify-center py-12 px-4 text-center space-y-3"
                >
                  <div className="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl bg-emerald-500/10 text-emerald-500 shadow-sm">
                    🌸
                  </div>
                  <div>
                    <h3 className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>
                      No flower image analyzed yet
                    </h3>
                    <p className="text-[11px] mt-1 leading-relaxed max-w-[220px]" style={{ color: 'var(--text-muted)' }}>
                      Upload a flower photo above or paste an image in chat to view complete species care card here.
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </aside>

        {/* RIGHT CENTRAL CHAT WORKSPACE */}
        <div
          className={`
            flex-1 flex flex-col overflow-hidden min-h-0
            ${mobileTab === 'chat' ? 'flex' : 'hidden lg:flex'}
          `}
          style={{ background: 'var(--surface)' }}
        >
          <ChatWindow />
        </div>
      </div>
    </div>
  )
}

