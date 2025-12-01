import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { User, Bot, Film, ChevronDown, ChevronUp, GitBranch, Search, Zap, Clock, Database } from 'lucide-react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import type { Movie, Reasoning } from '../api/client'

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
              {recommendations.slice(0, 8).map((movie) => (
                <Link
                  key={movie.movie_id}
                  to={`/movie/${movie.movie_id}`}
                  className="group relative overflow-hidden rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-all hover:scale-105 hover:shadow-xl"
                >
                  {/* Poster */}
                  <div className="aspect-[2/3] overflow-hidden">
                    {movie.poster_path ? (
                      <img
                        src={`https://image.tmdb.org/t/p/w300${movie.poster_path}`}
                        alt={movie.title}
                        className="w-full h-full object-cover transition-transform group-hover:scale-110"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center">
                        <Film className="w-8 h-8 text-slate-600" />
                      </div>
                    )}
                  </div>
                  
                  {/* Overlay with info */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent opacity-100">
                    <div className="absolute bottom-0 left-0 right-0 p-2">
                      <h4 className="text-xs font-medium text-white truncate">
                        {movie.title}
                      </h4>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-[10px] text-slate-400">
                          {movie.release_year || 'N/A'}
                        </span>
                        {movie.vote_average && movie.vote_average > 0 && (
                          <span className="text-[10px] text-yellow-400 flex items-center gap-0.5">
                            ★ {movie.vote_average.toFixed(1)}
                          </span>
                        )}
                      </div>
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

        {/* Reasoning Toggle */}
        {!isUser && reasoning && (
          <button
            onClick={() => setShowReasoning(!showReasoning)}
            className="flex items-center gap-2 text-xs text-slate-500 hover:text-cinema-400 transition-colors"
          >
            <GitBranch className="w-3 h-3" />
            {showReasoning ? 'Hide' : 'Show'} how this was found
            {showReasoning ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {reasoning.total_time_ms && (
              <span className="text-slate-600">({reasoning.total_time_ms}ms)</span>
            )}
          </button>
        )}

        {/* Reasoning Panel */}
        <AnimatePresence>
          {!isUser && reasoning && showReasoning && (
            <ReasoningPanel reasoning={reasoning} />
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

function ReasoningPanel({ reasoning }: { reasoning: Reasoning }) {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="w-full max-w-2xl glass rounded-xl border border-slate-700/50 overflow-hidden"
    >
      <div className="p-4 border-b border-slate-700/50 bg-slate-800/30">
        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
          <Zap className="w-4 h-4 text-cinema-400" />
          How your results were found
        </h4>
        <p className="text-xs text-slate-400 mt-1">{reasoning.summary}</p>
      </div>

      <div className="p-4 space-y-4">
        {/* Steps */}
        <div className="space-y-3">
          {reasoning.steps.map((step, index) => (
            <div key={index} className="flex gap-3">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-cinema-500/20 flex items-center justify-center">
                <span className="text-xs text-cinema-400 font-bold">{step.step}</span>
              </div>
              <div className="flex-1">
                <h5 className="text-sm font-medium text-white">{step.name}</h5>
                <p className="text-xs text-slate-400 mt-0.5">{step.description}</p>
                {step.result && (
                  <div className="mt-2 text-xs">
                    {Object.entries(step.result).map(([key, value]) => (
                      <div key={key} className="flex gap-2 text-slate-500">
                        <span className="text-slate-600">{key.replace(/_/g, ' ')}:</span>
                        <span className="text-slate-300">
                          {typeof value === 'object' 
                            ? JSON.stringify(value) 
                            : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Graph Visualization */}
        {reasoning.graph_traversal && (
          <div className="border-t border-slate-700/50 pt-4">
            <h5 className="text-sm font-medium text-white flex items-center gap-2 mb-3">
              <Database className="w-4 h-4 text-blue-400" />
              Knowledge Graph Query
            </h5>
            
            {/* Simple Graph Visualization */}
            <div className="bg-slate-900/50 rounded-lg p-4 mb-3">
              <div className="flex flex-wrap items-center justify-center gap-4">
                {reasoning.graph_traversal.nodes.slice(0, 6).map((node) => (
                  <div
                    key={node.id}
                    className="flex flex-col items-center gap-1"
                  >
                    <div
                      className="w-12 h-12 rounded-full flex items-center justify-center text-white text-xs font-medium shadow-lg"
                      style={{ backgroundColor: node.color }}
                    >
                      {node.type[0]}
                    </div>
                    <span className="text-xs text-slate-400 max-w-[80px] truncate text-center">
                      {node.label}
                    </span>
                  </div>
                ))}
              </div>
              
              {/* Edge Labels */}
              {reasoning.graph_traversal.edges.length > 0 && (
                <div className="flex justify-center mt-3 gap-2 flex-wrap">
                  {[...new Set(reasoning.graph_traversal.edges.map(e => e.label))].map((label) => (
                    <span
                      key={label}
                      className="px-2 py-0.5 rounded text-xs bg-slate-700/50 text-slate-300"
                    >
                      {label}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Cypher Query */}
            <div className="bg-slate-900/70 rounded-lg p-3 font-mono text-xs text-slate-300 overflow-x-auto">
              <pre className="whitespace-pre-wrap">{reasoning.graph_traversal.cypher_query}</pre>
            </div>
          </div>
        )}

        {/* Similarity Search Info */}
        {reasoning.similarity_search && (
          <div className="border-t border-slate-700/50 pt-4">
            <h5 className="text-sm font-medium text-white flex items-center gap-2 mb-3">
              <Search className="w-4 h-4 text-amber-400" />
              Graph Similarity Search
            </h5>
            <div className="bg-slate-900/50 rounded-lg p-3 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Source movie:</span>
                <span className="text-slate-300 font-medium">
                  {reasoning.similarity_search.source_movie}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Method:</span>
                <span className="text-slate-300">{reasoning.similarity_search.method}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-slate-500">Scoring:</span>
                <span className="text-slate-300 text-xs bg-slate-800/50 px-2 py-1 rounded">
                  {reasoning.similarity_search.scoring}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Gemini Analysis Info */}
        {reasoning.gemini_analysis && (
          <div className="border-t border-slate-700/50 pt-4">
            <h5 className="text-sm font-medium text-white flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-purple-400" />
              Gemini AI Analysis
            </h5>
            <div className="bg-slate-900/50 rounded-lg p-3 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Model:</span>
                <span className="text-slate-300">{reasoning.gemini_analysis.model}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Query Type:</span>
                <span className="text-slate-300 font-medium text-cinema-400">
                  {reasoning.gemini_analysis.parsed_type || reasoning.gemini_analysis.query_type}
                </span>
              </div>
              {reasoning.gemini_analysis.entities && Object.keys(reasoning.gemini_analysis.entities).length > 0 && (
                <div className="flex flex-col gap-1">
                  <span className="text-slate-500">Extracted:</span>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(reasoning.gemini_analysis.entities).map(([key, value]) => (
                      value && (
                        <span key={key} className="px-2 py-0.5 bg-slate-800 rounded text-slate-300">
                          {key}: {Array.isArray(value) ? value.join(', ') : String(value)}
                        </span>
                      )
                    ))}
                  </div>
                </div>
              )}
              {reasoning.gemini_analysis.reason && (
                <div className="flex flex-col gap-1">
                  <span className="text-slate-500">Note:</span>
                  <span className="text-amber-400/80 text-xs">
                    {reasoning.gemini_analysis.reason}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Timing */}
        <div className="flex items-center justify-end gap-2 text-xs text-slate-500 pt-2 border-t border-slate-700/50">
          <Clock className="w-3 h-3" />
          Total time: {reasoning.total_time_ms}ms
        </div>
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
