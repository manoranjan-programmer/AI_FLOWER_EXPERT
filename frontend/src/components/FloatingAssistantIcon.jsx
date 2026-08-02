import { motion } from 'framer-motion'
import { Sparkles, MessageSquare, ScanLine } from 'lucide-react'
import { useApp } from '../context/AppContext'

export default function FloatingAssistantIcon() {
  const { state, setView } = useApp()
  const { currentView } = state

  if (currentView === 'chat') return null

  return (
    <div className="fixed bottom-6 right-6 z-40 flex items-center gap-2">
      <motion.button
        whileHover={{ scale: 1.08, y: -2 }}
        whileTap={{ scale: 0.94 }}
        onClick={() => setView('chat')}
        className="flex items-center gap-2 px-4 py-3 rounded-full text-white font-bold text-xs shadow-2xl glow-effect cursor-pointer"
        style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}
      >
        <Sparkles className="w-4 h-4 animate-spin" />
        <span>Open AI Chat</span>
      </motion.button>
    </div>
  )
}
