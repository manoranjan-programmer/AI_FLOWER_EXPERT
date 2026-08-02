import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  User,
  LogOut,
  ShieldCheck,
  Moon,
  Sun,
  ChevronDown,
  Sparkles,
  Mail,
  Calendar,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useApp } from '../context/AppContext'

export default function UserProfileMenu() {
  const { user, logout } = useAuth()
  const { state, toggleTheme, showToast } = useApp()
  const { theme } = state
  const [isOpen, setIsOpen] = useState(false)
  const [imgError, setImgError] = useState(false)
  const menuRef = useRef(null)

  // Close dropdown on outside click or Escape
  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }
    function handleKeyDown(e) {
      if (e.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  if (!user) return null

  const getInitials = (name) => {
    if (!name) return 'AI'
    const parts = name.trim().split(' ')
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    return name.slice(0, 2).toUpperCase()
  }

  const handleLogout = async () => {
    setIsOpen(false)
    await logout()
    showToast('Signed out of AI Flower Expert. See you soon! 🌸', 'info')
  }

  const formattedDate = user.created_at
    ? new Date(user.created_at).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
    : 'Member'

  return (
    <div ref={menuRef} className="relative z-50">
      {/* Top-Right Avatar Button */}
      <motion.button
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 p-1 pl-1.5 pr-2.5 rounded-full border glass-panel transition-all duration-200 cursor-pointer shadow-xs"
        style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}
        title={`${user.name} (${user.email})`}
      >
        {user.picture && !imgError ? (
          <img
            src={user.picture}
            alt={user.name}
            onError={() => setImgError(true)}
            className="w-7 h-7 rounded-full object-cover border border-emerald-500/40 shadow-xs"
          />
        ) : (
          <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-emerald-500 to-teal-400 text-white font-bold text-xs flex items-center justify-center shadow-xs">
            {getInitials(user.name)}
          </div>
        )}

        <span className="font-semibold text-xs hidden sm:inline-block max-w-[100px] truncate" style={{ color: 'var(--text-primary)' }}>
          {user.name.split(' ')[0]}
        </span>

        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </motion.button>

      {/* Floating User Profile Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.96 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="absolute right-0 mt-2 w-72 rounded-3xl border shadow-2xl p-4 glass-panel overflow-hidden"
            style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
          >
            {/* Header: Avatar, Name, Email, Role */}
            <div className="flex items-start gap-3 pb-3 border-b" style={{ borderColor: 'var(--border)' }}>
              {user.picture && !imgError ? (
                <img
                  src={user.picture}
                  alt={user.name}
                  className="w-11 h-11 rounded-2xl object-cover border-2 border-emerald-500/50 shadow-md flex-shrink-0"
                />
              ) : (
                <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-white font-bold text-sm flex items-center justify-center shadow-md flex-shrink-0">
                  {getInitials(user.name)}
                </div>
              )}

              <div className="flex-1 min-w-0">
                <h4 className="font-bold text-sm truncate" style={{ color: 'var(--text-primary)' }}>
                  {user.name}
                </h4>
                <div className="flex items-center gap-1 text-[11px] truncate mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  <Mail className="w-3 h-3 flex-shrink-0" />
                  <span className="truncate">{user.email}</span>
                </div>

                <div className="mt-1.5 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-500 border border-emerald-500/30">
                  <ShieldCheck className="w-3 h-3" />
                  <span className="capitalize">{user.role || 'Botanist User'}</span>
                </div>
              </div>
            </div>

            {/* Account Details info */}
            <div className="py-2.5 space-y-1 text-[11px]" style={{ color: 'var(--text-secondary)' }}>
              <div className="flex items-center justify-between px-2 py-1 rounded-xl hover:bg-slate-500/5">
                <span className="flex items-center gap-1.5 text-slate-400">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>Member Since</span>
                </span>
                <span className="font-semibold">{formattedDate}</span>
              </div>
            </div>

            {/* Actions: Theme Toggle & Logout */}
            <div className="pt-2 border-t space-y-1" style={{ borderColor: 'var(--border)' }}>
              <button
                onClick={toggleTheme}
                className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold hover:bg-slate-500/10 transition-colors cursor-pointer"
                style={{ color: 'var(--text-primary)' }}
              >
                <span className="flex items-center gap-2">
                  {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-400" />}
                  <span>{theme === 'dark' ? 'Light Theme' : 'Dark Theme'}</span>
                </span>
                <span className="text-[10px] text-slate-400 capitalize">{theme}</span>
              </button>

              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold text-rose-500 hover:bg-rose-500/15 transition-colors cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
                <span>Sign Out</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
