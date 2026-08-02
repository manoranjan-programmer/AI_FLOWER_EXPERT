import { motion } from 'framer-motion'
import { ScanLine, Sparkles, Image as ImageIcon, ArrowLeft } from 'lucide-react'
import { useApp } from '../context/AppContext'
import ImageUpload from '../components/ImageUpload'
import PredictionCard from '../components/PredictionCard'

export default function IdentificationPage() {
  const { state, setView } = useApp()
  const { prediction, isPredicting } = state

  return (
    <div className="flex-1 flex flex-col overflow-y-auto p-4 sm:p-8" style={{ background: 'var(--surface)' }}>
      <div className="max-w-4xl mx-auto w-full space-y-8">
        {/* Page Header */}
        <div className="text-center space-y-3 border-b pb-6" style={{ borderColor: 'var(--border)' }}>
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-bold bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">
            <ScanLine className="w-3.5 h-3.5" />
            <span>EfficientNet AI Vision Classifier</span>
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-black tracking-tight" style={{ color: 'var(--text-primary)' }}>
            Identify Flower Species
          </h1>
          <p className="text-xs sm:text-sm max-w-lg mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Upload any flower photo to instantly identify species, check pet toxicity, view medicinal properties, and generate plant care guides.
          </p>
        </div>

        {/* Upload Zone */}
        <div className="max-w-xl mx-auto">
          <ImageUpload />
        </div>

        {/* Prediction Results */}
        {isPredicting && (
          <div className="max-w-2xl mx-auto space-y-3 p-6 rounded-3xl border glass-panel">
            <div className="h-6 w-1/3 rounded-xl animate-shimmer" />
            <div className="h-4 w-2/3 rounded-xl animate-shimmer" />
            <div className="h-24 w-full rounded-2xl animate-shimmer" />
          </div>
        )}

        {prediction && !isPredicting && (
          <div className="max-w-2xl mx-auto">
            <PredictionCard prediction={prediction} />
          </div>
        )}
      </div>
    </div>
  )
}

