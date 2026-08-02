import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useApp } from '../context/AppContext'
import Navbar from './Navbar'
import Sidebar from './Sidebar'
import ToastNotification from './ToastNotification'
import KeyboardShortcutsModal from './KeyboardShortcutsModal'
import FloatingAssistantIcon from './FloatingAssistantIcon'
import FeedbackModal from './FeedbackModal'

const pageVariants = {
  initial: { opacity: 0, y: 8 },
  enter: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15, ease: 'easeIn' } },
}

export default function Layout({ children }) {
  const { state, setActiveModal, toggleTheme, resetChat } = useApp()
  const { activeModal } = state

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Cmd/Ctrl + K -> Toggle Keyboard Shortcuts
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setActiveModal(activeModal === 'shortcuts' ? null : 'shortcuts')
      }
      // Esc -> Close modals
      if (e.key === 'Escape') {
        setActiveModal(null)
      }
      // Cmd/Ctrl + Shift + N -> New Chat
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'n') {
        e.preventDefault()
        resetChat()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [activeModal, setActiveModal, resetChat])

  return (
    <div className="flex h-dvh w-screen overflow-hidden select-none" style={{ background: 'var(--surface)' }}>
      {/* Collapsible Left Sidebar */}
      <Sidebar />

      {/* Main Container */}
      <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden relative">
        {/* Top Navbar */}
        <Navbar />

        {/* Dynamic Page Content */}
        <main className="flex-1 flex flex-col h-full min-h-0 overflow-hidden relative">
          {children}
        </main>
      </div>

      {/* Global Modals & Notifications */}
      <ToastNotification />
      <KeyboardShortcutsModal />
      <FeedbackModal />
      <FloatingAssistantIcon />
    </div>
  )
}
