import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AppProvider, useApp } from './context/AppContext'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import LandingPage from './pages/LandingPage'
import ChatPage from './pages/ChatPage'
import IdentificationPage from './pages/IdentificationPage'
import FavoritesPage from './pages/FavoritesPage'
import LoginPage from './pages/LoginPage'
import ImageModalViewer from './components/ImageModalViewer'
import { Flower2 } from 'lucide-react'

const pageVariants = {
  initial: { opacity: 0, scale: 0.99 },
  enter: { opacity: 1, scale: 1, transition: { duration: 0.22, ease: 'easeOut' } },
  exit: { opacity: 0, scale: 0.99, transition: { duration: 0.15, ease: 'easeIn' } },
}

function AppContent() {
  const { state } = useApp()
  const { currentView, theme } = state
  const { isAuthenticated, isAuthLoading } = useAuth()

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [theme])

  if (isAuthLoading) {
    return (
      <div className="h-dvh w-screen flex items-center justify-center relative overflow-hidden" style={{ background: 'var(--surface)' }}>
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="w-14 h-14 rounded-3xl bg-emerald-500/20 text-emerald-500 flex items-center justify-center shadow-lg glow-effect">
            <Flower2 className="w-7 h-7 animate-spin-slow" />
          </div>
          <span className="text-xs font-bold animate-pulse text-slate-400">Authenticating session...</span>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LoginPage />
  }

  const renderView = () => {
    switch (currentView) {
      case 'landing':
        return <LandingPage />
      case 'chat':
        return <ChatPage />
      case 'identify':
        return <IdentificationPage />
      case 'favorites':
        return <FavoritesPage />
      default:
        return <ChatPage />
    }
  }

  return (
    <>
      <Layout>
        <AnimatePresence mode="wait">
          <motion.div
            key={currentView}
            variants={pageVariants}
            initial="initial"
            animate="enter"
            exit="exit"
            className="flex-1 flex flex-col h-full min-h-0 overflow-hidden"
          >
            {renderView()}
          </motion.div>
        </AnimatePresence>
      </Layout>

      {/* Fullscreen Image Zoom Viewer Overlay */}
      <ImageModalViewer />
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppProvider>
        <AppContent />
      </AppProvider>
    </AuthProvider>
  )
}
