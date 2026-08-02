import { motion, AnimatePresence } from 'framer-motion'
import { FiX, FiSun, FiMoon, FiGlobe, FiCheck } from 'react-icons/fi'
import { useApp } from '../context/AppContext'

const LANGUAGES = [
  { code: 'en', label: 'English',            flag: '🇬🇧' },
  { code: 'ta', label: 'Tamil (தமிழ்)',      flag: '🇮🇳' },
  { code: 'hi', label: 'Hindi (हिंदी)',      flag: '🇮🇳' },
  { code: 'ml', label: 'Malayalam (മലയാളം)', flag: '🇮🇳' },
  { code: 'te', label: 'Telugu (తెలుగు)',    flag: '🇮🇳' },
  { code: 'kn', label: 'Kannada (கன்னட)',    flag: '🇮🇳' },
  { code: 'es', label: 'Spanish (Español)',  flag: '🇪🇸' },
  { code: 'fr', label: 'French (Français)',  flag: '🇫🇷' },
  { code: 'de', label: 'German (Deutsch)',   flag: '🇩🇪' },
]

export default function Settings({ isOpen, onClose }) {
  const { state, toggleTheme, setLanguage, translateLastAnswer } = useApp()
  const { theme, language } = state

  const handleLang = (code) => {
    setLanguage(code)
    if (code !== 'en') translateLastAnswer(code)
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            key="bd"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0,0,0,0.3)' }}
          />

          {/* Panel */}
          <motion.aside
            key="panel"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 320 }}
            className="fixed top-0 right-0 h-full w-72 z-50 flex flex-col"
            style={{
              background: 'var(--surface)',
              borderLeft: '1px solid var(--border)',
              boxShadow: '-8px 0 32px rgba(0,0,0,0.08)',
            }}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-5 h-14 flex-shrink-0"
              style={{ borderBottom: '1px solid var(--border)' }}
            >
              <h2 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                Settings
              </h2>
              <button onClick={onClose} className="btn-ghost !px-2 !py-2">
                <FiX size={17} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-6 space-y-7">

              {/* Theme */}
              <section>
                <p
                  className="text-xs font-semibold uppercase tracking-widest mb-3"
                  style={{ color: 'var(--text-muted)' }}
                >
                  Theme
                </p>
                <div className="grid grid-cols-1 gap-2">
                  <div
                    className="flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all duration-150"
                    style={{
                      background: 'var(--accent-light)',
                      border: '1.5px solid var(--accent)',
                      color: 'var(--accent)',
                    }}
                  >
                    <FiSun size={14} />
                    Light Mode
                  </div>
                </div>
              </section>

              {/* Language */}
              <section>
                <p
                  className="text-xs font-semibold uppercase tracking-widest mb-3 flex items-center gap-1.5"
                  style={{ color: 'var(--text-muted)' }}
                >
                  <FiGlobe size={11} />
                  Response Language
                </p>
                <div className="space-y-1.5">
                  {LANGUAGES.map(({ code, label, flag }) => (
                    <button
                      key={code}
                      onClick={() => handleLang(code)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg
                                 text-sm font-medium transition-all duration-150"
                      style={{
                        background: language === code ? 'var(--accent-light)' : 'var(--surface-2)',
                        border: `1px solid ${language === code ? 'var(--accent)' : 'var(--border)'}`,
                        color: language === code ? 'var(--accent)' : 'var(--text-primary)',
                      }}
                    >
                      <span className="text-base">{flag}</span>
                      <span>{label}</span>
                      {language === code && (
                        <FiCheck size={13} className="ml-auto" style={{ color: 'var(--accent)' }} />
                      )}
                    </button>
                  ))}
                </div>
                {language !== 'en' && (
                  <p className="text-xs mt-2.5 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                    Last AI response will be translated. Future responses auto-translate.
                  </p>
                )}
              </section>
            </div>

            {/* Footer */}
            <div
              className="px-5 py-4 flex-shrink-0"
              style={{ borderTop: '1px solid var(--border)' }}
            >
              <p className="text-xs text-center" style={{ color: 'var(--text-muted)' }}>
                Flower AI Expert v1.0 · All models run locally
              </p>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
