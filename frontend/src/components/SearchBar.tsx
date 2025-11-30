import { useState, FormEvent } from 'react'
import { Search, X, Sparkles } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'

interface SearchBarProps {
  onSearch: (query: string) => void
  placeholder?: string
  loading?: boolean
  showSemanticHint?: boolean
  className?: string
  size?: 'default' | 'large'
}

export function SearchBar({
  onSearch,
  placeholder = 'Search movies...',
  loading = false,
  showSemanticHint = true,
  className,
  size = 'default',
}: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [isFocused, setIsFocused] = useState(false)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(query.trim())
    }
  }

  const handleClear = () => {
    setQuery('')
  }

  return (
    <form onSubmit={handleSubmit} className={className}>
      <div
        className={clsx(
          'relative group',
          isFocused && 'ring-2 ring-cinema-500/50',
          size === 'large' ? 'rounded-2xl' : 'rounded-xl'
        )}
      >
        {/* Glow effect */}
        <div
          className={clsx(
            'absolute -inset-0.5 bg-gradient-to-r from-cinema-500/20 to-cinema-600/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity blur',
            isFocused && 'opacity-100'
          )}
        />
        
        {/* Input container */}
        <div
          className={clsx(
            'relative glass flex items-center gap-3 overflow-hidden',
            size === 'large' ? 'rounded-2xl px-6 py-4' : 'rounded-xl px-4 py-3'
          )}
        >
          {/* Search icon */}
          <Search
            className={clsx(
              'flex-shrink-0 transition-colors',
              isFocused ? 'text-cinema-400' : 'text-slate-400',
              size === 'large' ? 'w-6 h-6' : 'w-5 h-5'
            )}
          />
          
          {/* Input */}
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder}
            className={clsx(
              'flex-1 bg-transparent border-none focus:outline-none text-white placeholder-slate-500',
              size === 'large' ? 'text-lg' : 'text-base'
            )}
          />
          
          {/* Clear button */}
          <AnimatePresence>
            {query && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                type="button"
                onClick={handleClear}
                className="p-1 hover:bg-slate-700/50 rounded-full transition-colors"
              >
                <X className="w-4 h-4 text-slate-400" />
              </motion.button>
            )}
          </AnimatePresence>
          
          {/* Search button */}
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className={clsx(
              'flex-shrink-0 flex items-center gap-2 bg-gradient-to-r from-cinema-500 to-cinema-600 text-white font-medium rounded-lg transition-all hover:from-cinema-600 hover:to-cinema-700 disabled:opacity-50 disabled:cursor-not-allowed',
              size === 'large' ? 'px-6 py-2.5' : 'px-4 py-2'
            )}
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span className="hidden sm:inline">Search</span>
              </>
            )}
          </button>
        </div>
      </div>
      
      {/* Semantic search hint */}
      {showSemanticHint && (
        <p className="mt-2 text-xs text-slate-500 text-center">
          Try natural language: "sci-fi movies like Inception" or "feel-good comedies from the 90s"
        </p>
      )}
    </form>
  )
}

