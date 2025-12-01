import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  Star, Clock, Calendar, DollarSign, 
  Users, Clapperboard, ArrowLeft
} from 'lucide-react'
import { MovieCard } from '../components/MovieCard'
import { metadataApi } from '../api/client'
import type { MovieDetail, Movie } from '../api/client'

const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p'
const BACKDROP_SIZE = '/w1280'
const POSTER_SIZE = '/w500'

export function MovieDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [movie, setMovie] = useState<MovieDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchMovie = async () => {
      if (!id) return
      
      setLoading(true)
      try {
        const movieId = parseInt(id)
        
        // Single API call - movie details + similar movies fetched in parallel on backend
        const movieData = await metadataApi.getMovie(movieId, true, 6)
        setMovie(movieData)
      } catch (error) {
        console.error('Failed to fetch movie:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchMovie()
  }, [id])
  
  // Extract similar movies from the movie detail response
  const similarMovies: Movie[] = movie?.similar_movies?.map(m => ({
    movie_id: m.movie_id,
    title: m.title,
    overview: m.overview,
    release_year: m.release_year,
    vote_average: m.vote_average,
    poster_path: m.poster_path,
    genres: m.genres,
    score: m.similarity_score / 20, // Normalize to 0-1
    explanation: m.match_reason
  })) || []

  if (loading) {
    return <MovieDetailSkeleton />
  }

  if (!movie) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white mb-2">Movie not found</h2>
          <Link to="/search" className="text-cinema-400 hover:text-cinema-300">
            Back to search
          </Link>
        </div>
      </div>
    )
  }

  const backdropUrl = movie.backdrop_path
    ? `${TMDB_IMAGE_BASE}${BACKDROP_SIZE}${movie.backdrop_path}`
    : null
  const posterUrl = movie.poster_path
    ? `${TMDB_IMAGE_BASE}${POSTER_SIZE}${movie.poster_path}`
    : 'https://i.imgur.com/xPgvLg9.png'

  return (
    <div className="min-h-screen">
      {/* Backdrop */}
      {backdropUrl && (
        <div className="absolute inset-x-0 top-0 h-[60vh] overflow-hidden">
          <img
            src={backdropUrl}
            alt=""
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-midnight-950 via-midnight-950/80 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-midnight-950/90 via-transparent to-midnight-950/90" />
        </div>
      )}

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        {/* Back Button */}
        <Link
          to="/search"
          className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-8"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to search
        </Link>

        {/* Main Content */}
        <div className="grid lg:grid-cols-[300px,1fr] gap-8 lg:gap-12">
          {/* Poster */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="relative"
          >
            <div className="aspect-[2/3] rounded-2xl overflow-hidden shadow-2xl border border-slate-700/50">
              <img
                src={posterUrl}
                alt={movie.title}
                className="w-full h-full object-cover"
              />
            </div>
          </motion.div>

          {/* Info */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            {/* Title & Rating */}
            <div className="flex flex-wrap items-start gap-4 mb-4">
              <h1 className="font-display text-4xl lg:text-5xl font-bold text-white">
                {movie.title}
              </h1>
              {movie.vote_average && movie.vote_average > 0 && (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-yellow-500/20 text-yellow-400">
                  <Star className="w-5 h-5 fill-yellow-400" />
                  <span className="font-semibold">{movie.vote_average.toFixed(1)}</span>
                </div>
              )}
            </div>

            {/* Genres */}
            <div className="flex flex-wrap gap-2 mb-6">
              {movie.genres.map((genre) => (
                <Link
                  key={genre}
                  to={`/search?genres=${genre}`}
                  className="px-3 py-1 rounded-full text-sm bg-cinema-500/20 text-cinema-400 hover:bg-cinema-500/30 transition-colors"
                >
                  {genre}
                </Link>
              ))}
            </div>

            {/* Quick Stats */}
            <div className="flex flex-wrap gap-6 text-slate-400 text-sm mb-8">
              {movie.release_year && (
                <span className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  {movie.release_year}
                </span>
              )}
              {movie.runtime && (
                <span className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  {Math.floor(movie.runtime / 60)}h {movie.runtime % 60}m
                </span>
              )}
              {movie.vote_count && (
                <span className="flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  {movie.vote_count.toLocaleString()} votes
                </span>
              )}
            </div>

            {/* Overview */}
            {movie.overview && (
              <div className="mb-8">
                <h2 className="text-lg font-semibold text-white mb-3">Overview</h2>
                <p className="text-slate-300 leading-relaxed">{movie.overview}</p>
              </div>
            )}

            {/* Directors */}
            {movie.directors && movie.directors.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-slate-400 mb-2 flex items-center gap-2">
                  <Clapperboard className="w-4 h-4" />
                  Director{movie.directors.length > 1 ? 's' : ''}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {movie.directors.map((director) => (
                    <span
                      key={director.id}
                      className="px-3 py-1 rounded-lg bg-slate-700/50 text-white text-sm"
                    >
                      {director.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Cast */}
            {movie.cast && movie.cast.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-slate-400 mb-2 flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  Cast
                </h3>
                <div className="flex flex-wrap gap-2">
                  {movie.cast.slice(0, 8).map((actor) => (
                    <span
                      key={actor.id}
                      className="px-3 py-1 rounded-lg bg-slate-700/50 text-white text-sm"
                      title={actor.character}
                    >
                      {actor.name}
                    </span>
                  ))}
                  {movie.cast.length > 8 && (
                    <span className="px-3 py-1 rounded-lg bg-slate-700/50 text-slate-400 text-sm">
                      +{movie.cast.length - 8} more
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Financial Stats */}
            {(movie.budget || movie.revenue) && (
              <div className="flex flex-wrap gap-6 text-sm">
                {movie.budget && movie.budget > 0 && (
                  <div>
                    <span className="text-slate-400 flex items-center gap-1 mb-1">
                      <DollarSign className="w-4 h-4" />
                      Budget
                    </span>
                    <span className="text-white font-medium">
                      ${movie.budget.toLocaleString()}
                    </span>
                  </div>
                )}
                {movie.revenue && movie.revenue > 0 && (
                  <div>
                    <span className="text-slate-400 flex items-center gap-1 mb-1">
                      <DollarSign className="w-4 h-4" />
                      Revenue
                    </span>
                    <span className="text-white font-medium">
                      ${movie.revenue.toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        </div>

        {/* Similar Movies */}
        {similarMovies.length > 0 && (
          <section className="mt-16 pb-16">
            <h2 className="font-display text-2xl font-bold text-white mb-6">
              Similar Movies
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {similarMovies.map((movie, index) => (
                <MovieCard key={movie.movie_id} movie={movie} index={index} showScore />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

function MovieDetailSkeleton() {
  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-[300px,1fr] gap-8 lg:gap-12">
          <div className="aspect-[2/3] rounded-2xl bg-slate-800/50 animate-shimmer" />
          <div className="space-y-4">
            <div className="h-12 bg-slate-800/50 rounded animate-shimmer w-3/4" />
            <div className="h-6 bg-slate-800/50 rounded animate-shimmer w-1/2" />
            <div className="h-32 bg-slate-800/50 rounded animate-shimmer" />
          </div>
        </div>
      </div>
    </div>
  )
}

