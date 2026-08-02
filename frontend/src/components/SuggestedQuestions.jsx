import { motion } from 'framer-motion'
import { Sparkles, Sun, ShieldAlert, HeartPulse, Droplets, ArrowRight } from 'lucide-react'
import { useApp } from '../context/AppContext'

const SUGGESTED_CARDS = [
  {
    icon: Sun,
    title: 'Sunlight & Water Schedule',
    prompt: 'What are the sunlight and watering schedule requirements for Sunflowers and Roses?',
  },
  {
    icon: ShieldAlert,
    title: 'Plant Toxicity Check',
    prompt: 'Is Oleander or Jasmine toxic to domestic cats and dogs?',
  },
  {
    icon: HeartPulse,
    title: 'Medicinal Uses & Benefits',
    prompt: 'What are the medicinal properties and therapeutic uses of Chamomile and Lavender?',
  },
  {
    icon: Droplets,
    title: 'Leaf Spot Diagnosis & Cure',
    prompt: 'How do I identify and treat black fungal spots on rose leaves naturally?',
  },
]

export default function SuggestedQuestions() {
  const { sendMessage } = useApp()

  return (
    <div className="w-full max-w-4xl mx-auto py-6 px-4">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-bold mb-3 border bg-emerald-500/10 border-emerald-500/30 text-emerald-500">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Interactive Botanical AI Assistant</span>
        </div>
        <h2 className="font-display text-2xl sm:text-4xl font-black tracking-tight" style={{ color: 'var(--text-primary)' }}>
          What would you like to explore today?
        </h2>
        <p className="text-xs sm:text-sm mt-2 max-w-lg mx-auto" style={{ color: 'var(--text-secondary)' }}>
          Select a prompt chip below or type any question about flower species, pet toxicity, or plant care.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
        {SUGGESTED_CARDS.map((item, idx) => {
          const IconComp = item.icon
          return (
            <motion.button
              key={item.title}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08 }}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => sendMessage(item.prompt)}
              className="p-5 rounded-3xl text-left border transition-all duration-200 glass-panel card-modern flex items-start gap-4 group cursor-pointer"
            >
              <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-500 group-hover:bg-emerald-500 group-hover:text-white transition-colors duration-200 flex-shrink-0 shadow-xs">
                <IconComp className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="font-display font-bold text-xs sm:text-sm group-hover:text-emerald-500 transition-colors" style={{ color: 'var(--text-primary)' }}>
                    {item.title}
                  </h3>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400 opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                </div>
                <p className="text-xs leading-relaxed line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
                  "{item.prompt}"
                </p>
              </div>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}

