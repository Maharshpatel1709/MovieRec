import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { User, Bot, Film, ChevronDown, ChevronUp, GitBranch, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import type { Movie, Reasoning } from '../api/client'
import { GraphVisualization } from './GraphVisualization'

// Simple markdown parser for bold text
function parseMarkdown(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      const content = part.slice(2, -2)
      return <strong key={index} className="text-cinema-400 font-semibold">{content}</strong>
    }
    return <span key={index}>{part}</span>
  })
}

interface ChatBubbleProps {
  message: string
  isUser: boolean
  recommendations?: Movie[]
  reasoning?: Reasoning
  isTyping?: boolean
}

export function ChatBubble({ message, isUser, recommendations, reasoning, isTyping }: ChatBubbleProps) {
  const [showReasoning, setShowReasoning] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        'flex gap-3 max-w-4xl',
        isUser ? 'ml-auto flex-row-reverse' : ''
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center',
          isUser
            ? 'bg-gradient-to-br from-cinema-500 to-cinema-600'
            : 'bg-gradient-to-br from-slate-600 to-slate-700'
        )}
      >
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>

      {/* Content */}
      <div className={clsx('flex flex-col gap-3', isUser ? 'items-end' : 'items-start')}>
        {/* Message bubble */}
        <div
          className={clsx(
            'max-w-lg px-4 py-3',
            isUser ? 'chat-bubble-user text-white' : 'chat-bubble-assistant text-slate-200'
          )}
        >
          {isTyping ? (
            <div className="flex items-center gap-1 py-1">
              <span className="typing-dot w-2 h-2 bg-slate-400 rounded-full" />
              <span className="typing-dot w-2 h-2 bg-slate-400 rounded-full" />
              <span className="typing-dot w-2 h-2 bg-slate-400 rounded-full" />
            </div>
          ) : (
            <div className="text-sm leading-relaxed">
              {message.split('\n\n').map((paragraph, pIndex) => (
                <p key={pIndex} className="mb-2 last:mb-0">
                  {parseMarkdown(paragraph)}
                </p>
              ))}
            </div>
          )}
        </div>

        {/* Movie Cards Grid */}
        {!isUser && recommendations && recommendations.length > 0 && (
          <div className="w-full max-w-4xl">
            <p className="text-xs text-slate-500 mb-3 flex items-center gap-1">
              <Film className="w-3 h-3" />
              {recommendations.length} movies found
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {recommendations.slice(0, 10).map((movie) => (
                <Link
                  key={movie.movie_id}
                  to={`/movie/${movie.movie_id}`}
                  className="group relative overflow-hidden rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-all hover:scale-105 hover:shadow-xl"
                >
                  {/* Poster */}
                  <div className="aspect-[2/3] overflow-hidden bg-slate-800">
                    <img
                      src={movie.poster_path 
                        ? `https://image.tmdb.org/t/p/w300${movie.poster_path}`
                        : 'https://i.imgur.com/xPgvLg9.png'}
                      alt={movie.title}
                      className="w-full h-full object-cover transition-transform group-hover:scale-110"
                      loading="lazy"
                      onError={(e) => {
                        const img = e.target as HTMLImageElement
                        if (!img.src.includes('imgur.com')) {
                          img.src = 'https://i.imgur.com/xPgvLg9.png'
                        }
                      }}
                    />
                  </div>
                  
                  {/* Overlay with info */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent opacity-100">
                    <div className="absolute bottom-0 left-0 right-0 p-2">
                      <h4 className="text-xs font-medium text-white truncate">
                        {movie.title}
                      </h4>
                      {movie.genres && movie.genres.length > 0 && (
                        <div className="flex gap-1 mt-1 flex-wrap">
                          {movie.genres.slice(0, 2).map((genre) => (
                            <span
                              key={genre}
                              className="text-[9px] px-1.5 py-0.5 bg-cinema-500/30 text-cinema-300 rounded"
                            >
                              {genre}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Match reason tooltip on hover */}
                  {movie.match_reason && (
                    <div className="absolute top-0 left-0 right-0 p-2 bg-black/80 text-[9px] text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity">
                      {movie.match_reason}
                    </div>
                  )}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Extracted Entities */}
        {!isUser && reasoning?.gemini_analysis?.entities && (
          <div className="flex flex-wrap gap-2 max-w-4xl">
            {Object.entries(reasoning.gemini_analysis.entities).map(([key, value]) => (
              value && !['mood_genres'].includes(key) && (
                <span 
                  key={key} 
                  className="px-2 py-1 bg-slate-800/50 rounded-lg text-xs text-slate-300 flex items-center gap-1"
                >
                  <Sparkles className="w-3 h-3 text-cinema-400" />
                  <span className="text-slate-500">{key}:</span>
                  <span className="text-white font-medium">
                    {Array.isArray(value) ? value.join(', ') : String(value)}
                  </span>
                </span>
              )
            ))}
          </div>
        )}

        {/* Graph Toggle */}
        {!isUser && reasoning && (
          <button
            onClick={() => setShowReasoning(!showReasoning)}
            className="flex items-center gap-2 text-xs text-slate-500 hover:text-cinema-400 transition-colors"
          >
            <GitBranch className="w-3 h-3" />
            {showReasoning ? 'Hide' : 'Show'} knowledge graph
            {showReasoning ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        )}

        {/* Graph Visualization */}
        <AnimatePresence>
          {!isUser && reasoning && showReasoning && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="w-full max-w-4xl"
            >
              <GraphVisualization reasoning={reasoning} recommendations={recommendations} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

export function SuggestionChips({
  suggestions,
  onSelect
}: {
  suggestions: string[]
  onSelect: (suggestion: string) => void
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {suggestions.map((suggestion, index) => (
        <motion.button
          key={suggestion}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: index * 0.05 }}
          onClick={() => onSelect(suggestion)}
          className="px-3 py-1.5 rounded-full text-sm bg-slate-700/50 text-slate-300 hover:bg-cinema-500/20 hover:text-cinema-400 border border-slate-600/50 hover:border-cinema-500/30 transition-all"
        >
          {suggestion}
        </motion.button>
      ))}
    </div>
  )
}
