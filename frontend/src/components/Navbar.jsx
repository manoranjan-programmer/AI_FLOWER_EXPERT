import { motion } from 'framer-motion'
import {
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  MessageSquare,
  ScanLine,
  Heart,
  Sun,
  Moon,
  Command,
  Volume2,
  Flower2,
} from 'lucide-react'
import { useApp } from '../context/AppContext'
import UserProfileMenu from './UserProfileMenu'

export default function Navbar() {
  const { state, toggleSidebar, toggleTheme, setView, setActiveModal } = useApp()
  const { sidebarOpen, theme, currentView, favorites, speakingMessageId } = state

  const NAV_ITEMS = [
    { id: 'chat', label: 'AI Chatbot', icon: MessageSquare },
    { id: 'identify', label: 'Image Identifier', icon: ScanLine },
    { id: 'favorites', label: `Saved (${favorites.length})`, icon: Heart },
  ]

  return (
    <header className="h-[64px] flex-shrink-0 flex items-center justify-between px-4 sm:px-6 z-30 glass-header sticky top-0">
      {/* Left side: Sidebar Toggle & Brand */}
      <div className="flex items-center gap-3">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={toggleSidebar}
          className="p-2 rounded-xl border transition-colors hover:bg-slate-500/10 cursor-pointer"
          style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
          title={sidebarOpen ? 'Collapse Sidebar' : 'Expand Sidebar'}
        >
          {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
        </motion.button>

        {/* View Title & AI Model Badge */}
        <div className="flex items-center gap-2.5">
          <div
            onClick={() => setView('chat')}
            className="flex items-center gap-2 cursor-pointer group"
          >
            <span className="font-display text-sm font-black tracking-tight hidden sm:inline-block group-hover:text-emerald-500 transition-colors" style={{ color: 'var(--text-primary)' }}>
              Flower AI Expert
            </span>
          </div>

          <div
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border shadow-xs"
            style={{
              background: 'var(--accent-light)',
              borderColor: 'var(--accent)',
              color: 'var(--accent)',
            }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="hidden xs:inline">Phi-3.5 Vision AI</span>
            <span className="xs:hidden">AI</span>
          </div>
        </div>
      </div>

      {/* Center: View Switcher Tabs (Desktop & Tablet) */}
      <nav className="hidden md:flex items-center gap-1 p-1 rounded-2xl border glass-panel" style={{ background: 'var(--surface-3)', borderColor: 'var(--border)' }}>
        {NAV_ITEMS.map((item) => {
          const IconComp = item.icon
          const isActive = currentView === item.id
          return (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className="relative flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all duration-200 cursor-pointer select-none"
              style={{
                color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
              }}
            >
              {isActive && (
                <motion.div
                  layoutId="activeNavTab"
                  className="absolute inset-0 rounded-xl border shadow-sm"
                  style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}
                  transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                />
              )}
              <span className="relative z-10 flex items-center gap-1.5">
                <IconComp className="w-3.5 h-3.5" />
                {item.label}
              </span>
            </button>
          )
        })}
      </nav>

      {/* Right side Actions */}
      <div className="flex items-center gap-2">
        {/* Audio Speaking indicator if active */}
        {speakingMessageId && (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs bg-emerald-500/15 text-emerald-500 font-bold animate-pulse border border-emerald-500/30">
            <Volume2 className="w-3.5 h-3.5 animate-bounce" />
            <span className="text-[11px] hidden sm:inline">Speaking</span>
          </div>
        )}

        {/* Shortcuts Command Button */}
        <button
          onClick={() => setActiveModal('shortcuts')}
          className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-colors hover:bg-slate-500/10 cursor-pointer"
          style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}
          title="Keyboard Shortcuts (⌘K)"
        >
          <Command className="w-3.5 h-3.5 text-emerald-500" />
          <span>⌘K</span>
        </button>

        {/* User Profile Avatar Dropdown Menu */}
        <UserProfileMenu />
      </div>
    </header>
  )
}

