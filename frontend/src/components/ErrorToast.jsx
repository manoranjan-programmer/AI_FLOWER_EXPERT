import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FiAlertCircle, FiX } from 'react-icons/fi'
import { useApp } from '../context/AppContext'

export default function ErrorToast() {
  const { state, clearError } = useApp()
  const { error } = state

  useEffect(() => {
    if (!error) return
    const t = setTimeout(clearError, 6000)
    return () => clearTimeout(t)
  }, [error, clearError])

  return (
    <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 w-full max-w-md px-4">
      <AnimatePresence>
        {error && (
          <motion.div
            key={error}
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.96 }}
            transition={{ type: 'spring', damping: 22, stiffness: 320 }}
            className="flex items-start gap-3 p-4 rounded-xl shadow-lg"
            style={{
              background: '#fff1f2',
              border: '1px solid #fecdd3',
              boxShadow: '0 8px 24px rgba(0,0,0,0.1)',
            }}
          >
            <FiAlertCircle size={17} className="mt-0.5 flex-shrink-0" style={{ color: '#e11d48' }} />
            <p className="flex-1 text-sm" style={{ color: '#9f1239' }}>{error}</p>
            <button
              onClick={clearError}
              className="transition-opacity hover:opacity-60"
              style={{ color: '#e11d48' }}
              aria-label="Dismiss"
            >
              <FiX size={15} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
