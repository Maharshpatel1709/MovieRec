import { useState, useEffect } from 'react'
import { Filter, X, ChevronDown } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'
import { searchApi } from '../api/client'

interface GenreFilterProps {
  selectedGenres: string[]
  onGenresChange: (genres: string[]) => void
}

export function GenreFilter({ selectedGenres, onGenresChange }: GenreFilterProps) {
  const [genres, setGenres] = useState<string[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchGenres = async () => {
      try {
        const data = await searchApi.getGenres()
        setGenres(data.genres)
      } catch (error) {
        // Fallback genres
        setGenres([
          'Action', 'Adventure', 'Animation', 'Comedy', 'Crime',
          'Documentary', 'Drama', 'Family', 'Fantasy', 'History',
          'Horror', 'Music', 'Mystery', 'Romance', 'Science Fiction',
          'Thriller', 'War', 'Western'
        ])
      } finally {
        setLoading(false)
      }
    }
    fetchGenres()
  }, [])

  const toggleGenre = (genre: string) => {
    if (selectedGenres.includes(genre)) {
      onGenresChange(selectedGenres.filter(g => g !== genre))
    } else {
      onGenresChange([...selectedGenres, genre])
    }
  }

  const clearGenres = () => {
    onGenresChange([])
  }

  return (
    <div className="relative">
      {/* Toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'flex items-center gap-2 px-4 py-2 rounded-lg transition-all',
          selectedGenres.length > 0
            ? 'bg-cinema-500/20 text-cinema-400 border border-cinema-500/30'
            : 'glass border border-slate-700/50 text-slate-300 hover:text-white hover:border-slate-600'
        )}
      >
        <Filter className="w-4 h-4" />
        <span className="text-sm font-medium">
          {selectedGenres.length > 0 ? `${selectedGenres.length} selected` : 'Genres'}
        </span>
        <ChevronDown className={clsx(
          'w-4 h-4 transition-transform',
          isOpen && 'rotate-180'
        )} />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />
            
            {/* Panel */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute top-full left-0 mt-2 z-50 w-80 glass rounded-xl border border-slate-700/50 p-4 shadow-2xl"
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-medium text-white">Filter by Genre</h3>
                {selectedGenres.length > 0 && (
                  <button
                    onClick={clearGenres}
                    className="text-xs text-cinema-400 hover:text-cinema-300 flex items-center gap-1"
                  >
                    <X className="w-3 h-3" />
                    Clear all
                  </button>
                )}
              </div>

              {/* Genre grid */}
              {loading ? (
                <div className="grid grid-cols-3 gap-2">
                  {Array.from({ length: 12 }).map((_, i) => (
                    <div key={i} className="h-8 bg-slate-700/50 rounded animate-shimmer" />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-2 max-h-60 overflow-y-auto">
                  {genres.map((genre) => (
                    <button
                      key={genre}
                      onClick={() => toggleGenre(genre)}
                      className={clsx(
                        'px-3 py-1.5 rounded-lg text-xs font-medium transition-all text-left truncate',
                        selectedGenres.includes(genre)
                          ? 'bg-cinema-500 text-white'
                          : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700 hover:text-white'
                      )}
                    >
                      {genre}
                    </button>
                  ))}
                </div>
              )}

              {/* Selected tags */}
              {selectedGenres.length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-700/50">
                  <div className="flex flex-wrap gap-2">
                    {selectedGenres.map((genre) => (
                      <span
                        key={genre}
                        className="inline-flex items-center gap-1 px-2 py-1 bg-cinema-500/20 text-cinema-400 rounded-full text-xs"
                      >
                        {genre}
                        <button
                          onClick={() => toggleGenre(genre)}
                          className="hover:text-white"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}

