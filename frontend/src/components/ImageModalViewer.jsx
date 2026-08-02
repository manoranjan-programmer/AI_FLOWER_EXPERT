import { motion, AnimatePresence } from 'framer-motion'
import { X, ZoomIn, ZoomOut, RotateCw } from 'lucide-react'
import { useState } from 'react'
import { useApp } from '../context/AppContext'

export default function ImageModalViewer() {
  const { state, setActiveModal } = useApp()
  const { activeModal, modalImageSrc } = state
  const [scale, setScale] = useState(1)
  const [rotation, setRotation] = useState(0)

  if (activeModal !== 'image-viewer' || !modalImageSrc) return null

  const handleZoomIn = () => setScale((prev) => Math.min(prev + 0.3, 3))
  const handleZoomOut = () => setScale((prev) => Math.max(prev - 0.3, 0.5))
  const handleRotate = () => setRotation((prev) => (prev + 90) % 360)

  const handleClose = () => {
    setScale(1)
    setRotation(0)
    setActiveModal(null)
  }

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
        {/* Controls Overlay */}
        <div className="absolute top-4 right-4 flex items-center gap-2 z-10">
          <button
            onClick={handleZoomIn}
            className="p-2.5 rounded-xl bg-slate-900/80 text-white hover:bg-emerald-500 transition-colors shadow-md"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2.5 rounded-xl bg-slate-900/80 text-white hover:bg-emerald-500 transition-colors shadow-md"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleRotate}
            className="p-2.5 rounded-xl bg-slate-900/80 text-white hover:bg-emerald-500 transition-colors shadow-md"
            title="Rotate"
          >
            <RotateCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleClose}
            className="p-2.5 rounded-xl bg-slate-900/80 text-white hover:bg-rose-500 transition-colors shadow-md"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Image */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          className="max-w-4xl max-h-[85vh] overflow-hidden flex items-center justify-center p-2 select-none"
        >
          <img
            src={modalImageSrc}
            alt="Zoomed flower"
            className="max-w-full max-h-[80vh] object-contain rounded-2xl shadow-2xl transition-transform duration-200"
            style={{
              transform: `scale(${scale}) rotate(${rotation}deg)`,
            }}
          />
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
