import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus,
  MessageSquare,
  ScanLine,
  Heart,
  Search,
  Sparkles,
  ChevronRight,
  Flower2,
  Trash2,
  X,
  Sliders,
  CheckCircle2,
} from 'lucide-react'
import { useApp } from '../context/AppContext'

export default function Sidebar() {
  const { state, resetChat, setView, toggleFavorite, isFavorite, loadSession, setActiveModal } = useApp()
  const { sidebarOpen, currentView, history, favorites, prediction } = state
  const [searchQuery, setSearchQuery] = useState('')

  const filteredHistory = useMemo(() => {
    if (!searchQuery.trim()) return history
    const q = searchQuery.toLowerCase()
    return history.filter(
      (h) =>
        h.flower?.toLowerCase().includes(q) ||
        h.confidence?.toString().includes(q)
    )
  }, [history, searchQuery])

  const NAV_LINKS = [
    { id: 'chat', label: 'AI Chatbot', icon: MessageSquare },
    { id: 'identify', label: 'Image Identifier', icon: ScanLine },
    { id: 'favorites', label: 'Saved Species', icon: Heart, count: favorites.length },
  ]

  return (
    <AnimatePresence mode="wait">
      {sidebarOpen && (
        <motion.aside
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 280, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.22, ease: 'easeInOut' }}
          className="flex-shrink-0 flex flex-col h-full overflow-hidden z-20 border-r select-none glass-panel"
          style={{ borderColor: 'var(--border)', background: 'var(--surface-2)' }}
        >
          {/* TOP LOGO HEADER */}
          <div className="p-4 flex items-center justify-between border-b" style={{ borderColor: 'var(--border)' }}>
            <button
              onClick={() => setView('chat')}
              className="flex items-center gap-3 text-left group transition-transform active:scale-95 cursor-pointer"
            >
              <div className="w-9 h-9 rounded-2xl flex items-center justify-center bg-gradient-to-tr from-emerald-500 to-teal-400 text-white shadow-md glow-effect">
                <Flower2 className="w-5 h-5 group-hover:rotate-12 transition-transform duration-300" />
              </div>
              <div>
                <h1 className="font-display font-black text-sm tracking-tight flex items-center gap-1.5" style={{ color: 'var(--text-primary)' }}>
                  <span>Flower AI</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded-md bg-emerald-500/15 text-emerald-500 font-bold uppercase tracking-wider">Pro</span>
                </h1>
                <p className="text-[11px] font-medium" style={{ color: 'var(--text-muted)' }}>
                  Botanical Intelligence
                </p>
              </div>
            </button>
          </div>

          {/* NEW CHAT BUTTON */}
          <div className="p-3">
            <motion.button
              whileHover={{ scale: 1.02, y: -1 }}
              whileTap={{ scale: 0.98 }}
              onClick={resetChat}
              className="w-full flex items-center justify-center gap-2.5 py-3 px-4 rounded-2xl font-bold text-xs text-white shadow-lg transition-all cursor-pointer"
              style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}
            >
              <Plus className="w-4 h-4" />
              <span>New Conversation</span>
            </motion.button>
          </div>

          {/* SEARCH CONVERSATIONS & HISTORY */}
          <div className="px-3 pb-2">
            <div className="relative flex items-center">
              <Search className="w-3.5 h-3.5 absolute left-3 pointer-events-none" style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search species & chats..."
                className="w-full pl-9 pr-7 py-2 rounded-xl text-xs outline-none border transition-colors"
                style={{
                  background: 'var(--surface-3)',
                  borderColor: 'var(--border)',
                  color: 'var(--text-primary)',
                }}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 p-0.5 rounded-full hover:bg-slate-500/20"
                >
                  <X className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
                </button>
              )}
            </div>
          </div>

          {/* NAVIGATION LINKS */}
          <div className="px-2 py-1 space-y-0.5">
            {NAV_LINKS.map((link) => {
              const IconComp = link.icon
              const isActive = currentView === link.id
              return (
                <button
                  key={link.id}
                  onClick={() => setView(link.id)}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all duration-150 cursor-pointer"
                  style={{
                    background: isActive ? 'var(--accent-light)' : 'transparent',
                    color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                  }}
                >
                  <div className="flex items-center gap-2.5">
                    <IconComp className="w-4 h-4" />
                    <span>{link.label}</span>
                  </div>
                  {link.count !== undefined && link.count > 0 && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-500">
                      {link.count}
                    </span>
                  )}
                </button>
              )
            })}
          </div>

          {/* DIVIDER */}
          <div className="my-2 border-t px-4" style={{ borderColor: 'var(--border)' }} />

          {/* IDENTIFICATION HISTORY LIST */}
          <div className="flex-1 overflow-y-auto px-2 space-y-1">
            <div className="px-3 py-1 flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                Recent Analyses ({filteredHistory.length})
              </span>
            </div>

            {filteredHistory.length === 0 ? (
              <div className="py-8 text-center text-xs space-y-1" style={{ color: 'var(--text-muted)' }}>
                <p className="font-semibold">No species history yet</p>
                <p className="text-[10px]">Upload a flower photo to start tracking</p>
              </div>
            ) : (
              filteredHistory.map((item) => {
                const isSelected = prediction?.flower?.toLowerCase() === item.flower?.toLowerCase()
                return (
                  <motion.div
                    key={item.id}
                    whileHover={{ x: 2 }}
                    className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-all border group"
                    style={{
                      background: isSelected ? 'var(--surface-3)' : 'transparent',
                      borderColor: isSelected ? 'var(--accent)' : 'transparent',
                      color: 'var(--text-primary)',
                    }}
                    onClick={() => {
                      loadSession(item)
                    }}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      {item.imagePreview ? (
                        <img
                          src={item.imagePreview}
                          alt={item.flower}
                          className="w-7 h-7 rounded-lg object-cover border flex-shrink-0"
                          style={{ borderColor: 'var(--border)' }}
                        />
                      ) : (
                        <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center text-xs flex-shrink-0">
                          🌸
                        </div>
                      )}
                      <div className="truncate text-left min-w-0">
                        <p className="font-semibold truncate text-xs group-hover:text-emerald-500 transition-colors">
                          {item.flower}
                        </p>
                        <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                          {item.confidence ? `${item.confidence}%` : 'Analysis'} • {item.timestamp}
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        toggleFavorite(item)
                      }}
                      className="p-1 rounded-lg hover:bg-slate-500/15 transition-colors cursor-pointer"
                      title={isFavorite(item.flower) ? 'Remove Favorite' : 'Save Favorite'}
                    >
                      <Heart
                        className={`w-3.5 h-3.5 ${
                          isFavorite(item.flower) ? 'fill-rose-500 text-rose-500' : 'text-slate-400'
                        }`}
                      />
                    </button>
                  </motion.div>
                )
              })
            )}
          </div>

          {/* FOOTER USER / ENGINE STATUS */}
          <div className="p-3 border-t space-y-2" style={{ borderColor: 'var(--border)' }}>
            <button
              onClick={() => setActiveModal('shortcuts')}
              className="w-full flex items-center justify-between p-2.5 rounded-2xl border transition-colors hover:bg-slate-500/10 text-xs font-semibold cursor-pointer"
              style={{ background: 'var(--surface-3)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
            >
              <div className="flex items-center gap-2">
                <Sliders className="w-3.5 h-3.5 text-emerald-500" />
                <span>Shortcuts & Help</span>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>⌘K</span>
            </button>

            <div className="flex items-center justify-between p-2.5 rounded-2xl" style={{ background: 'var(--surface-3)' }}>
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-500 flex items-center justify-center font-bold text-xs">
                  AI
                </div>
                <div>
                  <p className="text-xs font-bold leading-none flex items-center gap-1" style={{ color: 'var(--text-primary)' }}>
                    <span>Flower Expert</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  </p>
                  <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                    102 Species Dataset
                  </p>
                </div>
              </div>
              <Flower2 className="w-4 h-4 text-emerald-500 animate-pulse" />
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  )
}

