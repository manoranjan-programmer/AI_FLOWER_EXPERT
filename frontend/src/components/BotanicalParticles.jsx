import { useMemo } from 'react'
import { motion } from 'framer-motion'

export default function BotanicalParticles({ count = 14 }) {
  const particles = useMemo(() => {
    const symbols = ['🌸', '🌺', '🌿', '🍃', '✨', '🌼', '🌻', '🌱']
    return Array.from({ length: count }).map((_, i) => ({
      id: i,
      symbol: symbols[i % symbols.length],
      left: Math.random() * 95,
      top: Math.random() * 95,
      size: Math.floor(Math.random() * 14) + 12,
      duration: Math.random() * 12 + 10,
      delay: Math.random() * 5,
    }))
  }, [count])

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
      {particles.map((p) => (
        <motion.div
          key={p.id}
          initial={{ opacity: 0, y: 0, rotate: 0 }}
          animate={{
            opacity: [0, 0.45, 0.8, 0.45, 0],
            y: [-20, -80, -140],
            rotate: [0, 45, 90, 180],
            x: [0, Math.sin(p.id) * 30, 0],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            delay: p.delay,
            ease: 'easeInOut',
          }}
          className="absolute select-none"
          style={{
            left: `${p.left}%`,
            top: `${p.top}%`,
            fontSize: `${p.size}px`,
            filter: 'drop-shadow(0 2px 8px rgba(16, 185, 129, 0.25))',
          }}
        >
          {p.symbol}
        </motion.div>
      ))}
    </div>
  )
}
