import { Link } from 'react-router-dom'
import { Star, Calendar } from 'lucide-react'
import { motion } from 'framer-motion'
import type { Movie, SearchResult } from '../api/client'

interface MovieCardProps {
  movie: Movie | SearchResult
  index?: number
}

const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500'
const PLACEHOLDER_IMAGE = 'https://i.imgur.com/xPgvLg9.png'

export function MovieCard({ movie, index = 0 }: MovieCardProps) {
  const posterUrl = movie.poster_path
    ? `${TMDB_IMAGE_BASE}${movie.poster_path}`
    : PLACEHOLDER_IMAGE

  const rating = movie.vote_average

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
    >
      <Link
        to={`/movie/${movie.movie_id}`}
        className="movie-card block group relative rounded-xl overflow-hidden bg-slate-800/50 border border-slate-700/50 hover:border-cinema-500/30"
      >
        {/* Poster */}
        <div className="aspect-[2/3] relative overflow-hidden">
          <img
            src={posterUrl}
            alt={movie.title}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
            loading="lazy"
            onError={(e) => {
              (e.target as HTMLImageElement).src = PLACEHOLDER_IMAGE
            }}
          />
          
          {/* Overlay gradient */}
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          
          {/* Rating badge */}
          {rating && rating > 0 && (
            <div className="absolute top-3 left-3">
              <div className="glass rounded-full px-2.5 py-1 flex items-center gap-1">
                <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
                <span className="text-xs font-semibold text-white">
                  {rating.toFixed(1)}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Info */}
        <div className="p-4">
          <h3 className="font-semibold text-white group-hover:text-cinema-400 transition-colors line-clamp-1">
            {movie.title}
          </h3>
          
          <div className="mt-2 flex items-center gap-3 text-sm text-slate-400">
            {movie.release_year && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                {movie.release_year}
              </span>
            )}
          </div>
          
          {/* Genres */}
          {movie.genres && movie.genres.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {movie.genres.slice(0, 2).map((genre) => (
                <span
                  key={genre}
                  className="px-2 py-0.5 rounded-full text-xs bg-slate-700/50 text-slate-300"
                >
                  {genre}
                </span>
              ))}
              {movie.genres.length > 2 && (
                <span className="px-2 py-0.5 rounded-full text-xs bg-slate-700/50 text-slate-400">
                  +{movie.genres.length - 2}
                </span>
              )}
            </div>
          )}
        </div>
      </Link>
    </motion.div>
  )
}

// Loading skeleton
export function MovieCardSkeleton() {
  return (
    <div className="rounded-xl overflow-hidden bg-slate-800/50 border border-slate-700/50">
      <div className="aspect-[2/3] animate-shimmer" />
      <div className="p-4 space-y-3">
        <div className="h-5 bg-slate-700/50 rounded animate-shimmer w-3/4" />
        <div className="h-4 bg-slate-700/50 rounded animate-shimmer w-1/2" />
        <div className="flex gap-2">
          <div className="h-5 bg-slate-700/50 rounded-full animate-shimmer w-16" />
          <div className="h-5 bg-slate-700/50 rounded-full animate-shimmer w-16" />
        </div>
      </div>
    </div>
  )
}

