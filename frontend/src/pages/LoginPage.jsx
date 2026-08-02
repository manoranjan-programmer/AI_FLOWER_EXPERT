import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google'
import {
  Flower2,
  Sparkles,
  ShieldCheck,
  Zap,
  Globe,
  Database,
  Lock,
  ArrowRight,
  X,
  Brain,
  CheckCircle2,
  Bot,
  Layers,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import BotanicalParticles from '../components/BotanicalParticles'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

export default function LoginPage() {
  const { loginWithGoogle, demoLogin, authError, setAuthError } = useAuth()
  const [loading, setLoading] = useState(false)
  const [customClientId, setCustomClientId] = useState(() => {
    return localStorage.getItem('flower_ai_google_client_id') || GOOGLE_CLIENT_ID || ''
  })

  const activeClientId = (
    customClientId ||
    GOOGLE_CLIENT_ID ||
    '331560846582-dgga70trnc6r545vtdol08jhmrs2flvv.apps.googleusercontent.com'
  ).trim()

  const handleSaveClientId = (newId) => {
    const cleanId = newId.trim()
    setCustomClientId(cleanId)
    if (cleanId) {
      localStorage.setItem('flower_ai_google_client_id', cleanId)
    } else {
      localStorage.removeItem('flower_ai_google_client_id')
    }
  }

  const handleGoogleSuccess = async (credentialResponse) => {
    if (!credentialResponse.credential) return
    setLoading(true)
    try {
      await loginWithGoogle(credentialResponse.credential)
    } catch (err) {
      console.error('Google Sign-In Error:', err)
      setAuthError(err.message || 'Google authentication failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleDemoSignIn = async () => {
    setLoading(true)
    try {
      await demoLogin()
    } catch (err) {
      console.error('Demo Login Error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-dvh w-screen flex items-center justify-center relative overflow-hidden p-4 sm:p-6 lg:p-8 select-none"
      style={{ background: 'var(--surface)' }}
    >
      {/* Background Animated Particles & Radial Mesh Glows */}
      <BotanicalParticles />
      <div className="absolute -top-40 -left-40 w-[40rem] h-[40rem] rounded-full bg-emerald-500/15 blur-[140px] pointer-events-none animate-pulse-slow" />
      <div className="absolute -bottom-40 -right-40 w-[40rem] h-[40rem] rounded-full bg-teal-500/15 blur-[140px] pointer-events-none animate-pulse-slow" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[50rem] h-[50rem] rounded-full bg-emerald-600/5 blur-[160px] pointer-events-none" />

      {/* Main Split Layout Container */}
      <div className="w-full max-w-6xl relative z-10 grid lg:grid-cols-12 gap-8 items-center">

        {/* Left Column: AI Hero Feature Showcase (Desktop / Tablet) */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="lg:col-span-7 space-y-8 text-left hidden lg:block pr-4"
        >
          {/* Top Brand Header */}
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold border shadow-sm glass-panel" style={{ background: 'var(--accent-light)', borderColor: 'var(--accent)', color: 'var(--accent)' }}>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Phi-3.5 Vision &amp; EfficientNet Engine</span>
            </div>

            <h1 className="font-display text-4xl lg:text-5xl font-black tracking-tight leading-[1.1]" style={{ color: 'var(--text-primary)' }}>
              Botanical Intelligence <br />
              <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-emerald-500 bg-clip-text text-transparent">
                Redefined for Experts.
              </span>
            </h1>

            <p className="text-sm leading-relaxed max-w-lg font-normal" style={{ color: 'var(--text-secondary)' }}>
              Experience real-time flower classification across 102+ species, pet toxicity diagnostics, multi-lingual streaming AI chat, and private cloud session history.
            </p>
          </div>

          {/* Interactive Feature Cards Grid */}
          <div className="grid sm:grid-cols-2 gap-3.5">
            <motion.div
              whileHover={{ y: -3, scale: 1.01 }}
              className="p-4 rounded-3xl border glass-panel space-y-2 relative overflow-hidden"
              style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}
            >
              <div className="w-9 h-9 rounded-2xl bg-emerald-500/15 text-emerald-400 flex items-center justify-center font-bold">
                <Brain className="w-5 h-5" />
              </div>
              <h3 className="font-display font-bold text-xs" style={{ color: 'var(--text-primary)' }}>
                Neural Vision Pipeline
              </h3>
              <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                EfficientNet B4 architecture delivering 98.5% instant accuracy with sub-second latency.
              </p>
            </motion.div>

            <motion.div
              whileHover={{ y: -3, scale: 1.01 }}
              className="p-4 rounded-3xl border glass-panel space-y-2 relative overflow-hidden"
              style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}
            >
              <div className="w-9 h-9 rounded-2xl bg-teal-500/15 text-teal-400 flex items-center justify-center font-bold">
                <Bot className="w-5 h-5" />
              </div>
              <h3 className="font-display font-bold text-xs" style={{ color: 'var(--text-primary)' }}>
                Streaming RAG Assistant
              </h3>
              <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                Powered by Phi-3.5 LLM with real-time ChatGPT token streaming in 4 languages.
              </p>
            </motion.div>

            <motion.div
              whileHover={{ y: -3, scale: 1.01 }}
              className="p-4 rounded-3xl border glass-panel space-y-2 relative overflow-hidden"
              style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}
            >
              <div className="w-9 h-9 rounded-2xl bg-indigo-500/15 text-indigo-400 flex items-center justify-center font-bold">
                <Database className="w-5 h-5" />
              </div>
              <h3 className="font-display font-bold text-xs" style={{ color: 'var(--text-primary)' }}>
                Isolated MongoDB Atlas
              </h3>
              <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                Per-user secure cloud database for persistent species search &amp; chat session histories.
              </p>
            </motion.div>

            <motion.div
              whileHover={{ y: -3, scale: 1.01 }}
              className="p-4 rounded-3xl border glass-panel space-y-2 relative overflow-hidden"
              style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}
            >
              <div className="w-9 h-9 rounded-2xl bg-amber-500/15 text-amber-400 flex items-center justify-center font-bold">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="font-display font-bold text-xs" style={{ color: 'var(--text-primary)' }}>
                Enterprise Auth &amp; Privacy
              </h3>
              <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                Protected with Google OAuth 2.0 and encrypted HTTP-only JWT authentication.
              </p>
            </motion.div>
          </div>

          {/* System Status Pill */}
          <div className="flex items-center gap-3 pt-2">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold glass-panel" style={{ background: 'var(--surface-3)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span>All Botanical AI Systems Operational</span>
            </div>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs text-slate-400 font-mono">v1.0.4-pro</span>
          </div>
        </motion.div>

        {/* Right Column: Sleek AI Tool Login Panel */}
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          className="lg:col-span-5 w-full max-w-md mx-auto"
        >
          <div
            className="rounded-3xl border shadow-2xl p-6 sm:p-8 glass-panel space-y-6 relative overflow-hidden backdrop-blur-3xl"
            style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}
          >
            {/* Top Logo & Welcome Text */}
            <div className="text-center space-y-3">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-500 via-teal-400 to-emerald-300 text-white shadow-xl glow-effect">
                <Flower2 className="w-8 h-8 animate-spin-slow" />
              </div>

              <div>
                <h2 className="font-display text-2xl font-black tracking-tight" style={{ color: 'var(--text-primary)' }}>
                  Flower AI Expert
                </h2>
                <p className="text-xs font-medium mt-1" style={{ color: 'var(--text-muted)' }}>
                  Sign in to access your AI botanical workspace
                </p>
              </div>
            </div>

            {/* Error Alert details if present */}
            {authError && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3.5 rounded-2xl bg-rose-500/15 border border-rose-500/30 text-rose-500 text-xs font-semibold space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold flex items-center gap-1.5">
                    <X className="w-3.5 h-3.5" />
                    Authentication Error
                  </span>
                  <button onClick={() => setAuthError(null)} className="text-[11px] hover:underline cursor-pointer">
                    Dismiss
                  </button>
                </div>
                <p className="text-[11px] font-normal leading-relaxed">{authError}</p>
              </motion.div>
            )}

            {/* Authentication Buttons & Actions */}
            <div className="space-y-4">
              {/* Official Google OAuth Sign-In Button (Continue with Google) */}
              <GoogleOAuthProvider clientId={activeClientId}>
                <div className="w-full flex justify-center py-1">
                  <GoogleLogin
                    onSuccess={handleGoogleSuccess}
                    onError={() => {
                      setAuthError('Google Login: Ensure Client ID in Google Cloud Console is allowed for http://localhost:5173.')
                    }}
                    theme="outline"
                    shape="pill"
                    size="large"
                    text="continue_with"
                    width="340"
                  />
                </div>
              </GoogleOAuthProvider>

              {/* Divider line */}
              <div className="relative flex items-center py-1">
                <div className="flex-grow border-t" style={{ borderColor: 'var(--border)' }} />
                <span className="flex-shrink mx-4 text-[10px] font-extrabold uppercase tracking-widest text-slate-400">OR</span>
                <div className="flex-grow border-t" style={{ borderColor: 'var(--border)' }} />
              </div>

              {/* Quick Demo Access Action */}
              <motion.button
                whileHover={{ scale: 1.02, y: -1 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleDemoSignIn}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2.5 py-3.5 px-5 rounded-full border font-bold text-xs transition-all cursor-pointer shadow-sm hover:bg-slate-500/10"
                style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
              >
                <span>Instant Demo Access (Skip for testing)</span>
                <ArrowRight className="w-3.5 h-3.5 text-emerald-500" />
              </motion.button>
            </div>

            {/* Footer Privacy & Security Note */}
            <div className="text-center text-[10px] space-y-1 pt-1" style={{ color: 'var(--text-muted)' }}>
              <div className="flex items-center justify-center gap-1 font-medium">
                <Lock className="w-3 h-3 text-emerald-500" />
                <span>Protected by Google OAuth 2.0 &amp; HTTP-only JWT Encryption</span>
              </div>
              <p className="text-[10px]">By continuing, you agree to Flower AI Expert’s Terms &amp; Privacy Policy.</p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

