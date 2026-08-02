import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Heart, Search, MessageSquare, Trash2, ArrowRight, Flower2, Sparkles } from 'lucide-react'
import { useApp } from '../context/AppContext'

export default function FavoritesPage() {
  const { state, setView, toggleFavorite, sendMessage } = useApp()
  const { favorites } = state
  const [search, setSearch] = useState('')

  const filteredFavorites = useMemo(() => {
    if (!search.trim()) return favorites
    const q = search.toLowerCase()
    return favorites.filter((f) => f.flower?.toLowerCase().includes(q))
  }, [favorites, search])

  return (
    <div className="flex-1 flex flex-col overflow-y-auto p-4 sm:p-8" style={{ background: 'var(--surface)' }}>
      <div className="max-w-5xl mx-auto w-full space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-6" style={{ borderColor: 'var(--border)' }}>
          <div>
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-bold bg-rose-500/10 border border-rose-500/30 text-rose-500 mb-2">
              <Heart className="w-3.5 h-3.5 fill-rose-500" />
              <span>Saved Botanical Garden</span>
            </div>
            <h1 className="font-display text-3xl sm:text-4xl font-black tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Favorite Flower Species
            </h1>
            <p className="text-xs sm:text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
              Quick access to your saved care guides, medicinal properties, and species profiles.
            </p>
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search saved flowers..."
              className="w-full pl-9 pr-4 py-2.5 rounded-2xl text-xs outline-none border transition-colors glass-panel"
              style={{
                background: 'var(--surface-2)',
                borderColor: 'var(--border)',
                color: 'var(--text-primary)',
              }}
            />
          </div>
        </div>

        {/* Favorites Grid */}
        {filteredFavorites.length === 0 ? (
          <div className="py-20 text-center space-y-4 rounded-3xl border glass-panel">
            <div className="w-14 h-14 rounded-3xl bg-rose-500/10 text-rose-500 flex items-center justify-center mx-auto text-2xl">
              ❤️
            </div>
            <div>
              <h3 className="font-display font-bold text-base" style={{ color: 'var(--text-primary)' }}>
                No favorite species saved yet
              </h3>
              <p className="text-xs mt-1 max-w-sm mx-auto" style={{ color: 'var(--text-muted)' }}>
                Click the heart icon on any analyzed flower card to save it here for quick plant care reference.
              </p>
            </div>
            <button
              onClick={() => setView('identify')}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl text-xs font-bold text-white shadow-md bg-emerald-500 hover:bg-emerald-600 transition-colors cursor-pointer"
            >
              <span>Identify a Flower</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredFavorites.map((item, idx) => (
              <motion.div
                key={item.flower}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: idx * 0.05 }}
                className="p-5 rounded-3xl border card-modern glass-panel flex flex-col justify-between space-y-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {item.imagePreview ? (
                      <img src={item.imagePreview} alt={item.flower} className="w-12 h-12 rounded-2xl object-cover border shadow-sm" style={{ borderColor: 'var(--border)' }} />
                    ) : (
                      <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold text-xl">
                        🌸
                      </div>
                    )}
                    <div>
                      <h3 className="font-display font-bold text-base" style={{ color: 'var(--text-primary)' }}>
                        {item.flower}
                      </h3>
                      {item.confidence && (
                        <p className="text-xs font-bold text-emerald-500 font-mono">
                          {item.confidence}% Match
                        </p>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => toggleFavorite(item)}
                    className="p-2 rounded-xl hover:bg-rose-500/10 text-rose-500 transition-colors cursor-pointer"
                    title="Remove from favorites"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="pt-3 border-t flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
                  <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                    Saved {item.savedAt ? new Date(item.savedAt).toLocaleDateString() : 'recently'}
                  </span>

                  <button
                    onClick={() => {
                      setView('chat')
                      sendMessage(`Provide complete care instructions and watering schedule for my saved ${item.flower}.`)
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-emerald-500 bg-emerald-500/10 hover:bg-emerald-500 hover:text-white transition-all cursor-pointer"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>Ask AI</span>
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

