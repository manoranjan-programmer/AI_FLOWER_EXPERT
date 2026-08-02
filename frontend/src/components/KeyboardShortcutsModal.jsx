import { motion, AnimatePresence } from 'framer-motion'
import { X, Command, CornerDownLeft, Sparkles, Image, RefreshCw, Moon } from 'lucide-react'
import { useApp } from '../context/AppContext'

const SHORTCUTS = [
  { key: 'Enter', desc: 'Send chat message', icon: CornerDownLeft },
  { key: 'Shift + Enter', desc: 'Add new line in chat input', icon: Command },
  { key: 'Ctrl / Cmd + K', desc: 'Toggle keyboard shortcuts menu', icon: Command },
  { key: 'Ctrl / Cmd + Shift + N', desc: 'Start a new AI conversation', icon: Sparkles },
  { key: 'Ctrl / Cmd + U', desc: 'Upload flower image', icon: Image },
  { key: 'Ctrl / Cmd + R', desc: 'Regenerate last AI response', icon: RefreshCw },
]

export default function KeyboardShortcutsModal() {
  const { state, setActiveModal } = useApp()
  const { activeModal } = state

  if (activeModal !== 'shortcuts') return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="w-full max-w-md rounded-3xl p-6 shadow-2xl glass-panel relative overflow-hidden"
          style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}
        >
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-700/20">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-emerald-500/10 text-emerald-500 font-bold">
                ⌘
              </div>
              <h3 className="font-display font-bold text-base" style={{ color: 'var(--text-primary)' }}>
                Keyboard Shortcuts
              </h3>
            </div>
            <button
              onClick={() => setActiveModal(null)}
              className="p-1.5 rounded-xl hover:bg-slate-500/10 transition-colors"
            >
              <X className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
            </button>
          </div>

          <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
            {SHORTCUTS.map((s) => {
              const IconComp = s.icon
              return (
                <div
                  key={s.key}
                  className="flex items-center justify-between p-2.5 rounded-2xl transition-colors hover:bg-slate-500/5"
                >
                  <div className="flex items-center gap-2.5">
                    <IconComp className="w-4 h-4 text-emerald-500" />
                    <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                      {s.desc}
                    </span>
                  </div>
                  <kbd className="px-2.5 py-1 rounded-lg text-[11px] font-mono font-semibold border shadow-xs" style={{ background: 'var(--surface-3)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
                    {s.key}
                  </kbd>
                </div>
              )
            })}
          </div>

          <div className="mt-5 pt-3 border-t border-slate-700/20 text-center">
            <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              Press <kbd className="px-1.5 py-0.5 rounded text-[10px] border" style={{ background: 'var(--surface-3)' }}>Esc</kbd> anytime to close dialogs.
            </p>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
