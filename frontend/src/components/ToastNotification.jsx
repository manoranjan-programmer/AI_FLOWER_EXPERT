import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react'
import { useApp } from '../context/AppContext'

export default function ToastNotification() {
  const { state, dispatch } = useApp()
  const { toast } = state

  if (!toast) return null

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-emerald-500" />
      case 'warning':
      case 'error':
        return <AlertCircle className="w-4 h-4 text-amber-500" />
      default:
        return <Info className="w-4 h-4 text-emerald-500" />
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-2xl shadow-2xl glass-panel border"
        style={{
          borderColor: 'var(--border)',
          background: 'var(--surface-overlay)',
        }}
      >
        {getIcon()}
        <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
          {toast.text}
        </span>
        <button
          onClick={() => dispatch({ type: 'CLEAR_TOAST' })}
          className="p-1 rounded-lg hover:bg-slate-500/10 transition-colors"
          aria-label="Close toast"
        >
          <X className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
        </button>
      </motion.div>
    </AnimatePresence>
  )
}
