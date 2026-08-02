import { motion } from 'framer-motion'
import { GiFlowerPot } from 'react-icons/gi'

export default function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="flex gap-3 px-4 py-4"
      style={{ borderBottom: '1px solid var(--border)' }}
    >
      {/* Avatar */}
      <div
        className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
        style={{ background: 'var(--accent)' }}
      >
        <GiFlowerPot size={15} className="text-white" />
      </div>

      {/* Dots */}
      <div className="flex items-center gap-1 py-2.5">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </div>
    </motion.div>
  )
}
