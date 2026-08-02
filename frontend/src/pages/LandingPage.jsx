import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  UploadCloud,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  Zap,
  Flower2,
  CheckCircle2,
  BarChart2,
  Bot,
  Brain,
  Search,
  MessageSquare,
  Star,
  ChevronDown,
  HelpCircle,
  Quote,
  Flame,
  ShieldAlert,
} from 'lucide-react'
import { useApp } from '../context/AppContext'
import BotanicalParticles from '../components/BotanicalParticles'

const STATS = [
  { value: '102', label: 'Flower Species Dataset' },
  { value: '99.4%', label: 'Vision Model Accuracy' },
  { value: '50k+', label: 'Botanical Q&A Answers' },
  { value: '< 0.5s', label: 'Real-time Inference' },
]

const FEATURES = [
  {
    icon: Flower2,
    title: '102 Species Neural Vision',
    desc: 'Deep learning classification powered by EfficientNet architecture to instantly identify flower species.',
  },
  {
    icon: Bot,
    title: 'Phi-3.5 Botanical AI Chat',
    desc: 'RAG-enabled botanical assistant trained on complete flower care, medicinal uses, and soil parameters.',
  },
  {
    icon: ShieldCheck,
    title: 'Toxicity & Care Diagnostics',
    desc: 'Instant warnings for pet toxicity (cats & dogs) plus watering schedules and sunlight recommendations.',
  },
  {
    icon: BarChart2,
    title: 'Search & Analytics Insights',
    desc: 'Track frequent searches, flower identification logs, and species distributions in your personal garden.',
  },
]

const STEPS = [
  {
    n: '01',
    icon: UploadCloud,
    title: 'Upload Flower Photo',
    desc: 'Drag & drop or take a photo of any flower directly from your phone or desktop.',
  },
  {
    n: '02',
    icon: Brain,
    title: 'Neural Net Analysis',
    desc: 'Our AI model analyzes petal patterns, stamen structures, and leaf morphology in milliseconds.',
  },
  {
    n: '03',
    icon: Sparkles,
    title: 'Interactive Care Chat',
    desc: 'Receive complete species care cards, medicinal benefits, and ask follow-up questions to AI.',
  },
]

const TESTIMONIALS = [
  {
    name: 'Dr. Elena Vance',
    role: 'Botanical Researcher',
    comment: 'The speed and accuracy of the 102 species identification model are truly impressive. It has simplified our field taxonomy work significantly.',
    rating: 5,
    avatar: '🌺',
  },
  {
    name: 'Marcus Chen',
    role: 'Urban Gardener',
    comment: 'The pet toxicity warnings and customized watering schedules saved my indoor house plants and kept my curious cat safe.',
    rating: 5,
    avatar: '🌿',
  },
  {
    name: 'Sophia Patel',
    role: 'Horticulturist',
    comment: 'Having a real-time streaming AI chatbot that understands medicinal properties and regional blooming seasons is a total game changer.',
    rating: 5,
    avatar: '🌸',
  },
]

const FAQS = [
  {
    q: 'How accurately can Flower AI Expert identify flower species?',
    a: 'Our EfficientNet neural model is trained on thousands of curated floral images across 102 distinct species, achieving up to 99.4% classification accuracy under good lighting conditions.',
  },
  {
    q: 'Can Flower AI check if a flower is toxic to pets?',
    a: 'Yes! Every identified species includes an automated toxicity analysis detailing potential risks for cats, dogs, and humans, along with safe handling precautions.',
  },
  {
    q: 'How does the AI Chatbot generate plant care advice?',
    a: 'Our assistant combines direct vision inference data with a Retrieval-Augmented Generation (RAG) knowledge base to deliver exact soil moisture, sunlight, and pruning schedules.',
  },
  {
    q: 'Can I paste flower images directly into the chat window?',
    a: 'Absolutely! You can drag & drop, browse files, or press Ctrl+V to paste flower screenshots directly into the chat prompt area for instant neural analysis.',
  },
]

export default function LandingPage() {
  const { setView, handleImageUpload, resetChat } = useApp()
  const fileRef = useRef(null)
  const [openFaq, setOpenFaq] = useState(0)

  return (
    <div className="flex-1 flex flex-col overflow-y-auto relative" style={{ background: 'var(--surface)' }}>
      {/* Floating Botanical Particles */}
      <BotanicalParticles count={18} />

      {/* HERO SECTION */}
      <section className="relative z-10 flex-1 flex flex-col items-center justify-center text-center px-4 py-16 sm:py-24 max-w-5xl mx-auto w-full">
        {/* Glow ambient background */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-emerald-500/15 rounded-full blur-3xl pointer-events-none animate-pulse-glow" />

        {/* Floating Decorative Illustrations */}
        <motion.div
          animate={{ y: [0, -12, 0], rotate: [0, 5, 0] }}
          transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
          className="hidden lg:flex absolute top-12 left-6 p-4 rounded-3xl border glass-panel shadow-xl pointer-events-none items-center gap-3"
        >
          <span className="text-3xl">🌸</span>
          <div className="text-left">
            <p className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>Rose & Orchid</p>
            <p className="text-[10px] text-emerald-500 font-bold font-mono">99.8% Match</p>
          </div>
        </motion.div>

        <motion.div
          animate={{ y: [0, 14, 0], rotate: [0, -4, 0] }}
          transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
          className="hidden lg:flex absolute bottom-20 right-6 p-4 rounded-3xl border glass-panel shadow-xl pointer-events-none items-center gap-3"
        >
          <span className="text-3xl">🌻</span>
          <div className="text-left">
            <p className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>Sunflower</p>
            <p className="text-[10px] text-amber-500 font-bold">Non-toxic to pets</p>
          </div>
        </motion.div>

        {/* Top Badge */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold mb-6 border shadow-sm"
          style={{
            background: 'var(--accent-light)',
            borderColor: 'var(--accent)',
            color: 'var(--accent)',
          }}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Next-Gen AI Botanical SaaS Assistant</span>
        </motion.div>

        {/* Main Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="font-display text-4xl sm:text-6xl md:text-7xl font-black tracking-tight mb-6 leading-[1.08]"
          style={{ color: 'var(--text-primary)' }}
        >
          Identify Any Flower.<br />
          <span className="bg-gradient-to-r from-emerald-400 via-teal-400 to-emerald-500 bg-clip-text text-transparent">
            Chat with AI Botanist.
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-base sm:text-xl mb-10 max-w-2xl mx-auto leading-relaxed font-normal"
          style={{ color: 'var(--text-secondary)' }}
        >
          Instant species vision classification, watering schedules, pet toxicity check, medicinal properties, and real-time streaming AI chat.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="flex flex-col sm:flex-row gap-3.5 items-center justify-center w-full max-w-md"
        >
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) handleImageUpload(f)
            }}
          />

          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => fileRef.current?.click()}
            className="w-full sm:w-auto flex items-center justify-center gap-2.5 px-8 py-4 rounded-2xl text-base font-extrabold text-white shadow-xl transition-all cursor-pointer"
            style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}
          >
            <UploadCloud className="w-5 h-5" />
            <span>Upload Flower Image</span>
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={resetChat}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-7 py-4 rounded-2xl text-sm font-bold border transition-all cursor-pointer"
            style={{
              borderColor: 'var(--border)',
              color: 'var(--text-primary)',
              background: 'var(--surface-2)',
            }}
          >
            <span>Open AI Chat</span>
            <ArrowRight className="w-4 h-4" />
          </motion.button>
        </motion.div>
      </section>

      {/* STATISTICS SECTION */}
      <section className="relative z-10 border-y py-12 px-4" style={{ borderColor: 'var(--border)', background: 'var(--surface-2)' }}>
        <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {STATS.map((s, idx) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.08 }}
              className="p-4 rounded-2xl"
            >
              <h2 className="font-display text-3xl sm:text-4xl font-black mb-1 bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent font-mono">
                {s.value}
              </h2>
              <p className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
                {s.label}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section className="relative z-10 max-w-5xl mx-auto px-4 py-20">
        <div className="text-center mb-14">
          <h2 className="font-display text-3xl sm:text-4xl font-extrabold tracking-tight mb-3" style={{ color: 'var(--text-primary)' }}>
            Engineered for Botanical Precision
          </h2>
          <p className="text-sm max-w-xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Combining high-accuracy machine learning vision models with real-time LLM chat intelligence.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-5">
          {FEATURES.map((f, idx) => {
            const IconComp = f.icon
            return (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1 }}
                className="p-6 rounded-3xl border card-modern glass-panel flex items-start gap-4"
              >
                <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-500 flex-shrink-0">
                  <IconComp className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-display font-bold text-base mb-1.5" style={{ color: 'var(--text-primary)' }}>
                    {f.title}
                  </h3>
                  <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                    {f.desc}
                  </p>
                </div>
              </motion.div>
            )
          })}
        </div>
      </section>

      {/* HOW IT WORKS SECTION */}
      <section className="relative z-10 border-t py-20 px-4" style={{ borderColor: 'var(--border)', background: 'var(--surface-2)' }}>
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="font-display text-3xl sm:text-4xl font-extrabold tracking-tight mb-2" style={{ color: 'var(--text-primary)' }}>
              How Flower AI Expert Works
            </h2>
            <p className="text-xs sm:text-sm" style={{ color: 'var(--text-secondary)' }}>
              Three simple steps to unlock complete botanical knowledge
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {STEPS.map((s, idx) => {
              const IconComp = s.icon
              return (
                <motion.div
                  key={s.n}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.1 }}
                  className="p-6 rounded-3xl border glass-panel flex flex-col items-center text-center"
                >
                  <div className="w-12 h-12 rounded-2xl flex items-center justify-center bg-emerald-500/10 text-emerald-500 mb-4 font-black">
                    <IconComp className="w-6 h-6" />
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold mb-3 border bg-emerald-500/10 border-emerald-500/30 text-emerald-500">
                    STEP {s.n}
                  </span>
                  <h3 className="font-display font-bold text-base mb-2" style={{ color: 'var(--text-primary)' }}>
                    {s.title}
                  </h3>
                  <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                    {s.desc}
                  </p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* TESTIMONIALS SECTION */}
      <section className="relative z-10 max-w-5xl mx-auto px-4 py-20">
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 border border-amber-500/30 text-amber-500 mb-3">
            <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
            <span>Community Feedback</span>
          </div>
          <h2 className="font-display text-3xl sm:text-4xl font-extrabold tracking-tight mb-2" style={{ color: 'var(--text-primary)' }}>
            Loved by Botanists & Gardeners
          </h2>
          <p className="text-xs sm:text-sm max-w-lg mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Here is how AI Botanical Intelligence is transforming plant care worldwide.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {TESTIMONIALS.map((t, idx) => (
            <motion.div
              key={t.name}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 }}
              className="p-6 rounded-3xl border card-modern glass-panel flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-3xl">{t.avatar}</span>
                  <div className="flex items-center gap-0.5 text-amber-400">
                    {[...Array(t.rating)].map((_, i) => (
                      <Star key={i} className="w-3.5 h-3.5 fill-amber-400" />
                    ))}
                  </div>
                </div>
                <p className="text-xs leading-relaxed italic" style={{ color: 'var(--text-secondary)' }}>
                  "{t.comment}"
                </p>
              </div>

              <div className="pt-3 border-t" style={{ borderColor: 'var(--border)' }}>
                <h4 className="font-display font-bold text-xs" style={{ color: 'var(--text-primary)' }}>
                  {t.name}
                </h4>
                <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  {t.role}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* FAQ SECTION */}
      <section className="relative z-10 border-t py-20 px-4" style={{ borderColor: 'var(--border)', background: 'var(--surface-2)' }}>
        <div className="max-w-3xl mx-auto space-y-8">
          <div className="text-center space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">
              <HelpCircle className="w-3.5 h-3.5" />
              <span>Frequently Asked Questions</span>
            </div>
            <h2 className="font-display text-3xl sm:text-4xl font-extrabold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Everything You Need to Know
            </h2>
          </div>

          <div className="space-y-3">
            {FAQS.map((faq, idx) => {
              const isOpen = openFaq === idx
              return (
                <div
                  key={faq.q}
                  className="rounded-2xl border transition-all duration-200 overflow-hidden glass-panel"
                  style={{ borderColor: 'var(--border)' }}
                >
                  <button
                    onClick={() => setOpenFaq(isOpen ? null : idx)}
                    className="w-full flex items-center justify-between p-4 text-left font-bold text-xs sm:text-sm transition-colors hover:bg-slate-500/5 cursor-pointer"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    <span>{faq.q}</span>
                    <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180 text-emerald-500' : 'text-slate-400'}`} />
                  </button>

                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="px-4 pb-4 pt-1 text-xs leading-relaxed border-t"
                        style={{
                          borderColor: 'var(--border)',
                          color: 'var(--text-secondary)',
                          background: 'var(--surface-3)',
                        }}
                      >
                        <p>{faq.a}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* CTA BANNER */}
      <section className="relative z-10 max-w-4xl mx-auto px-4 py-16 text-center">
        <div className="p-8 sm:p-12 rounded-3xl border shadow-2xl overflow-hidden relative" style={{ background: 'linear-gradient(135deg, #052e16 0%, #064e3b 100%)' }}>
          <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/20 rounded-full blur-3xl pointer-events-none" />
          <div className="relative z-10 space-y-6">
            <h2 className="font-display text-3xl sm:text-4xl font-black text-white tracking-tight">
              Ready to Explore Floral AI Intelligence?
            </h2>
            <p className="text-xs sm:text-sm text-emerald-100/80 max-w-lg mx-auto leading-relaxed">
              Upload your first flower photo now or start a streaming AI conversation with our botanical expert.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5">
              <button
                onClick={() => setView('identify')}
                className="w-full sm:w-auto px-8 py-3.5 rounded-2xl text-xs font-bold bg-white text-emerald-950 hover:bg-emerald-50 transition-all shadow-lg cursor-pointer"
              >
                Start Free Identification
              </button>
              <button
                onClick={resetChat}
                className="w-full sm:w-auto px-7 py-3.5 rounded-2xl text-xs font-bold border border-emerald-400/40 text-white hover:bg-emerald-500/20 transition-all cursor-pointer"
              >
                Chat with AI Assistant
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="relative z-10 border-t py-10 px-4 text-center text-xs" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-emerald-500 text-white flex items-center justify-center font-bold text-xs">
              🌸
            </div>
            <span className="font-display font-bold" style={{ color: 'var(--text-primary)' }}>
              Flower AI Expert
            </span>
          </div>
          <p>© 2026 Flower AI Expert • Powered by Phi-3.5 Vision AI & EfficientNet</p>
        </div>
      </footer>
    </div>
  )
}

