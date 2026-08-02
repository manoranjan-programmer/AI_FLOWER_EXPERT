import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { UploadCloud, Image as ImageIcon, X, Flower2, CheckCircle2, Scan } from 'lucide-react'
import { useApp } from '../context/AppContext'

export default function ImageUpload() {
  const { state, handleImageUpload, dispatch } = useApp()
  const { imagePreview, isPredicting, uploadProgress } = state

  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef(null)

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith('image/')) {
      handleImageUpload(file)
    }
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      handleImageUpload(file)
    }
  }

  const handleClear = () => {
    dispatch({ type: 'SET_IMAGE_PREVIEW', payload: null })
  }

  return (
    <div className="w-full">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileChange}
      />

      <AnimatePresence mode="wait">
        {imagePreview ? (
          /* PREVIEW STATE WITH SCANNER BEAM ANIMATION */
          <motion.div
            key="preview"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="relative rounded-3xl overflow-hidden border card-modern group shadow-xl"
            style={{ borderColor: 'var(--border)' }}
          >
            {/* Image Preview */}
            <div className="relative h-60 sm:h-64 w-full bg-slate-950 flex items-center justify-center overflow-hidden">
              <img
                src={imagePreview}
                alt="Flower preview"
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />

              {/* Glowing Laser Scanner & HUD Reticle Overlay during Prediction */}
              {isPredicting && (
                <div className="absolute inset-0 bg-emerald-950/40 backdrop-blur-xs pointer-events-none flex flex-col items-center justify-center">
                  {/* High-tech scanning grid background */}
                  <div
                    className="absolute inset-0 opacity-25"
                    style={{
                      backgroundImage: `radial-gradient(#10b981 1px, transparent 1px)`,
                      backgroundSize: '18px 18px',
                    }}
                  />

                  {/* Laser Scan Beam */}
                  <div className="absolute left-0 right-0 h-1.5 bg-gradient-to-r from-transparent via-emerald-400 to-transparent shadow-[0_0_25px_#10b981] animate-scanner" />

                  {/* Corner Target Reticles */}
                  <div className="absolute top-3 left-3 w-6 h-6 border-t-2 border-l-2 border-emerald-400" />
                  <div className="absolute top-3 right-3 w-6 h-6 border-t-2 border-r-2 border-emerald-400" />
                  <div className="absolute bottom-3 left-3 w-6 h-6 border-b-2 border-l-2 border-emerald-400" />
                  <div className="absolute bottom-3 right-3 w-6 h-6 border-b-2 border-r-2 border-emerald-400" />

                  {/* Center HUD Spinner & Stage Text */}
                  <div className="relative z-10 flex flex-col items-center px-4 py-3.5 rounded-2xl bg-black/75 border border-emerald-500/50 backdrop-blur-md shadow-2xl space-y-2 max-w-[250px]">
                    <div className="relative flex items-center justify-center">
                      <Scan className="w-10 h-10 text-emerald-400 animate-spin" />
                      <Flower2 className="w-4 h-4 text-teal-300 absolute animate-ping" />
                    </div>

                    <div className="text-center space-y-0.5">
                      <p className="text-[11px] font-extrabold text-white tracking-widest uppercase font-mono leading-tight">
                        {uploadProgress < 40
                          ? 'Neural Vision Scanning...'
                          : uploadProgress < 75
                          ? 'Extracting Floral Topology...'
                          : uploadProgress < 95
                          ? 'Matching 102 Species...'
                          : 'Finalizing Classification...'}
                      </p>
                      <p className="text-[10px] text-emerald-400 font-bold font-mono">
                        EfficientNet Vision Engine • {uploadProgress}%
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Clear button */}
              {!isPredicting && (
                <button
                  onClick={handleClear}
                  className="absolute top-3 right-3 p-1.5 rounded-full bg-black/70 text-white hover:bg-rose-500 transition-colors shadow-md cursor-pointer z-10"
                  title="Remove Image"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Upload Progress Bar */}
            {isPredicting && (
              <div className="p-3 border-t bg-slate-900/90 border-slate-800">
                <div className="flex items-center justify-between text-xs font-semibold text-white mb-1.5">
                  <span className="text-[11px] font-mono text-emerald-400">Scanning in Progress</span>
                  <span className="font-mono text-emerald-400">{uploadProgress}%</span>
                </div>
                <div className="w-full h-2.5 rounded-full bg-slate-800 overflow-hidden p-0.5 border border-emerald-500/30">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${uploadProgress}%` }}
                    className="h-full bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-300 rounded-full shadow-[0_0_12px_#10b981]"
                  />
                </div>
              </div>
            )}
          </motion.div>
        ) : (
          /* DRAG & DROP ZONE */
          <motion.div
            key="dropzone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              relative p-8 sm:p-10 rounded-3xl border-2 border-dashed cursor-pointer
              flex flex-col items-center justify-center text-center transition-all duration-200 glass-panel
              ${
                isDragging
                  ? 'border-emerald-500 bg-emerald-500/10 scale-[1.01]'
                  : 'hover:border-emerald-500/60 hover:bg-slate-500/5'
              }
            `}
            style={{
              borderColor: isDragging ? 'var(--accent)' : 'var(--border)',
              background: 'var(--surface-2)',
            }}
          >
            <div className="w-14 h-14 rounded-3xl flex items-center justify-center bg-emerald-500/10 text-emerald-500 mb-4 shadow-inner">
              <UploadCloud className="w-7 h-7" />
            </div>

            <h3 className="font-display font-bold text-sm sm:text-base mb-1" style={{ color: 'var(--text-primary)' }}>
              Drag & Drop flower photo here
            </h3>

            <p className="text-xs mb-4" style={{ color: 'var(--text-secondary)' }}>
              Supports JPG, PNG, WEBP up to 10MB
            </p>

            <div
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs font-bold text-white shadow-md transition-transform active:scale-95"
              style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}
            >
              <ImageIcon className="w-3.5 h-3.5" />
              <span>Browse Image File</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

