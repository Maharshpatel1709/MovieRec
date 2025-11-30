import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Film, Sparkles, TrendingUp, SlidersHorizontal, Star, Clock, Gem, Clapperboard } from 'lucide-react'
import { SearchBar } from '../components/SearchBar'
import { MovieCard, MovieCardSkeleton } from '../components/MovieCard'
import { GenreFilter } from '../components/GenreFilter'
import { searchApi, recommendationApi } from '../api/client'
import type { SearchResult, Movie } from '../api/client'
import clsx from 'clsx'

type SearchMode = 'smart' | 'filter'
type ExploreCategory = 'popular' | 'top_rated' | 'recent' | 'classic' | 'hidden_gems'

const EXPLORE_CATEGORIES: { id: ExploreCategory; label: string; icon: React.ReactNode; description: string }[] = [
  { id: 'popular', label: 'Popular', icon: <TrendingUp className="w-4 h-4" />, description: 'Most popular right now' },
  { id: 'top_rated', label: 'Top Rated', icon: <Star className="w-4 h-4" />, description: 'Highest rated movies' },
  { id: 'recent', label: 'Recent', icon: <Clock className="w-4 h-4" />, description: 'From 2020 onwards' },
  { id: 'classic', label: 'Classics', icon: <Clapperboard className="w-4 h-4" />, description: 'Pre-1990 gems' },
  { id: 'hidden_gems', label: 'Hidden Gems', icon: <Gem className="w-4 h-4" />, description: 'Underrated favorites' },
]

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [results, setResults] = useState<(SearchResult | Movie)[]>([])
  const [loading, setLoading] = useState(false)
  const [searchMode, setSearchMode] = useState<SearchMode>('smart')
  const [selectedGenres, setSelectedGenres] = useState<string[]>([])
  const [yearRange, setYearRange] = useState({ min: '', max: '' })
  const [minRating, setMinRating] = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const [activeCategory, setActiveCategory] = useState<ExploreCategory>('popular')
  const [searchType, setSearchType] = useState<string>('')
  const [detectedEntities, setDetectedEntities] = useState<Record<string, unknown> | null>(null)

  const initialQuery = searchParams.get('q') || ''

  // Initial search from URL
  useEffect(() => {
    if (initialQuery) {
      handleSearch(initialQuery)
    } else {
      loadCategory('popular')
    }
  }, [])

  const loadCategory = async (category: ExploreCategory) => {
    setLoading(true)
    setActiveCategory(category)
    setHasSearched(false)
    try {
      const data = await searchApi.explore(category, 20)
      setResults(data.results)
      setSearchType('explore')
    } catch (error) {
      console.error('Failed to load category:', error)
      // Fallback to popular
      try {
        const data = await recommendationApi.getPopular(undefined, 20)
        setResults(data.recommendations)
      } catch {
        setResults([])
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (query: string) => {
    setSearchParams({ q: query })
    setLoading(true)
    setHasSearched(true)
    setDetectedEntities(null)

    try {
      if (searchMode === 'smart') {
        const data = await searchApi.smart(query, 20)
        setResults(data.results)
        setSearchType(data.search_type)
        setDetectedEntities(data.detected_entities || null)
      } else {
        const data = await searchApi.movies({
          query,
          genres: selectedGenres.join(',') || undefined,
          year_min: yearRange.min ? parseInt(yearRange.min) : undefined,
          year_max: yearRange.max ? parseInt(yearRange.max) : undefined,
          rating_min: minRating ? parseFloat(minRating) : undefined,
          limit: 20,
        })
        setResults(data.results)
        setSearchType('filter')
      }
    } catch (error) {
      console.error('Search failed:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleFilterSearch = async () => {
    setLoading(true)
    setHasSearched(true)

    try {
      const data = await searchApi.movies({
        query: searchParams.get('q') || '',
        genres: selectedGenres.join(',') || undefined,
        year_min: yearRange.min ? parseInt(yearRange.min) : undefined,
        year_max: yearRange.max ? parseInt(yearRange.max) : undefined,
        rating_min: minRating ? parseFloat(minRating) : undefined,
        limit: 20,
      })
      setResults(data.results)
      setSearchType('filter')
    } catch (error) {
      console.error('Filter search failed:', error)
    } finally {
      setLoading(false)
    }
  }

  // Re-run filter search when filters change
  useEffect(() => {
    if (searchMode === 'filter' && hasSearched) {
      handleFilterSearch()
    }
  }, [selectedGenres, yearRange, minRating])

  const getSearchTypeLabel = () => {
    switch (searchType) {
      case 'similarity': return '🎯 Similar Movies'
      case 'director': return '🎬 Director Search'
      case 'actor': return '⭐ Actor Search'
      case 'genre': return '🎭 Genre Search'
      case 'decade': return '📅 Decade Search'
      case 'content': return '📝 Content Match'
      case 'text': return '🔤 Title Match'
      case 'filter': return '🔍 Filtered Search'
      case 'explore': return ''
      default: return '🔍 Smart Search'
    }
  }

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold text-white mb-2">
            Discover Movies
          </h1>
          <p className="text-slate-400">
            Search using natural language or browse by category
          </p>
        </div>

        {/* Explore Categories */}
        {!hasSearched && (
          <div className="mb-8">
            <h2 className="text-sm font-medium text-slate-400 mb-3">Explore</h2>
            <div className="flex flex-wrap gap-2">
              {EXPLORE_CATEGORIES.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => loadCategory(cat.id)}
                  className={clsx(
                    'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                    activeCategory === cat.id
                      ? 'bg-cinema-500 text-white'
                      : 'glass text-slate-400 hover:text-white hover:bg-slate-700/50'
                  )}
                >
                  {cat.icon}
                  {cat.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Search Controls */}
        <div className="space-y-4 mb-8">
          {/* Mode Toggle */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSearchMode('smart')}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                searchMode === 'smart'
                  ? 'bg-cinema-500 text-white'
                  : 'glass text-slate-400 hover:text-white'
              )}
            >
              <Sparkles className="w-4 h-4" />
              Smart Search
            </button>
            <button
              onClick={() => setSearchMode('filter')}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                searchMode === 'filter'
                  ? 'bg-cinema-500 text-white'
                  : 'glass text-slate-400 hover:text-white'
              )}
            >
              <SlidersHorizontal className="w-4 h-4" />
              Filter Search
            </button>
          </div>

          {/* Search Bar */}
          <SearchBar
            onSearch={handleSearch}
            placeholder={
              searchMode === 'smart'
                ? 'Try: "movies like Inception", "Christopher Nolan films", "90s thrillers"'
                : 'Search by title...'
            }
            loading={loading}
            showSemanticHint={false}
          />

          {/* Smart Search Hint */}
          {searchMode === 'smart' && !hasSearched && (
            <div className="glass rounded-lg p-4">
              <h3 className="text-sm font-medium text-white mb-2">💡 Smart Search Tips</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-400">
                <div>• <span className="text-cinema-400">"movies like The Hangover"</span> - Find similar movies</div>
                <div>• <span className="text-cinema-400">"Christopher Nolan films"</span> - Search by director</div>
                <div>• <span className="text-cinema-400">"Leonardo DiCaprio movies"</span> - Search by actor</div>
                <div>• <span className="text-cinema-400">"90s action movies"</span> - Search by decade & genre</div>
                <div>• <span className="text-cinema-400">"sci-fi thriller"</span> - Search by genre</div>
                <div>• <span className="text-cinema-400">"mind-bending psychological"</span> - Content search</div>
              </div>
            </div>
          )}

          {/* Detected Entities Banner */}
          {hasSearched && detectedEntities && Object.values(detectedEntities).some(v => v) && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass rounded-lg p-3 flex items-center gap-3"
            >
              <span className="text-sm text-slate-400">Detected:</span>
              <div className="flex flex-wrap gap-2">
                {detectedEntities.similar_to && (
                  <span className="px-2 py-1 rounded bg-amber-500/20 text-amber-400 text-xs">
                    Similar to: {String(detectedEntities.similar_to)}
                  </span>
                )}
                {detectedEntities.director && (
                  <span className="px-2 py-1 rounded bg-orange-500/20 text-orange-400 text-xs">
                    Director: {String(detectedEntities.director)}
                  </span>
                )}
                {detectedEntities.actor && (
                  <span className="px-2 py-1 rounded bg-green-500/20 text-green-400 text-xs">
                    Actor: {String(detectedEntities.actor)}
                  </span>
                )}
                {detectedEntities.genres && (
                  <span className="px-2 py-1 rounded bg-purple-500/20 text-purple-400 text-xs">
                    Genres: {(detectedEntities.genres as string[]).join(', ')}
                  </span>
                )}
                {detectedEntities.decade && (
                  <span className="px-2 py-1 rounded bg-blue-500/20 text-blue-400 text-xs">
                    Decade: {(detectedEntities.decade as number[])[0]}s
                  </span>
                )}
              </div>
            </motion.div>
          )}

          {/* Filters (shown in filter mode) */}
          {searchMode === 'filter' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex flex-wrap items-center gap-4"
            >
              <GenreFilter
                selectedGenres={selectedGenres}
                onGenresChange={setSelectedGenres}
              />
              
              {/* Year Range */}
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  placeholder="From year"
                  value={yearRange.min}
                  onChange={(e) => setYearRange(prev => ({ ...prev, min: e.target.value }))}
                  className="w-24 px-3 py-2 rounded-lg glass border border-slate-700/50 text-white text-sm placeholder-slate-500 focus:border-cinema-500/50"
                />
                <span className="text-slate-500">to</span>
                <input
                  type="number"
                  placeholder="To year"
                  value={yearRange.max}
                  onChange={(e) => setYearRange(prev => ({ ...prev, max: e.target.value }))}
                  className="w-24 px-3 py-2 rounded-lg glass border border-slate-700/50 text-white text-sm placeholder-slate-500 focus:border-cinema-500/50"
                />
              </div>

              {/* Min Rating */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-400">Min Rating:</span>
                <input
                  type="number"
                  placeholder="0"
                  min="0"
                  max="10"
                  step="0.5"
                  value={minRating}
                  onChange={(e) => setMinRating(e.target.value)}
                  className="w-20 px-3 py-2 rounded-lg glass border border-slate-700/50 text-white text-sm placeholder-slate-500 focus:border-cinema-500/50"
                />
              </div>
            </motion.div>
          )}
        </div>

        {/* Results Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2 text-slate-400">
            {hasSearched ? (
              <>
                <Film className="w-4 h-4" />
                <span>{results.length} results found</span>
                {searchType && searchType !== 'explore' && (
                  <span className="ml-2 px-2 py-0.5 rounded bg-slate-700/50 text-xs">
                    {getSearchTypeLabel()}
                  </span>
                )}
              </>
            ) : (
              <>
                {EXPLORE_CATEGORIES.find(c => c.id === activeCategory)?.icon}
                <span>{EXPLORE_CATEGORIES.find(c => c.id === activeCategory)?.description}</span>
              </>
            )}
          </div>
          {hasSearched && (
            <button
              onClick={() => {
                setHasSearched(false)
                setSearchParams({})
                setDetectedEntities(null)
                loadCategory('popular')
              }}
              className="text-sm text-cinema-400 hover:text-cinema-300"
            >
              Clear search
            </button>
          )}
        </div>

        {/* Results Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
          {loading
            ? Array.from({ length: 10 }).map((_, i) => <MovieCardSkeleton key={i} />)
            : results.map((movie, index) => (
                <MovieCard
                  key={movie.movie_id}
                  movie={movie}
                  index={index}
                  showScore={hasSearched && searchType === 'similarity'}
                />
              ))}
        </div>

        {/* Empty State */}
        {!loading && results.length === 0 && hasSearched && (
          <div className="text-center py-20">
            <Film className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No movies found</h3>
            <p className="text-slate-400 mb-4">
              Try adjusting your search or use different keywords
            </p>
            <button
              onClick={() => {
                setHasSearched(false)
                setSearchParams({})
                loadCategory('popular')
              }}
              className="px-4 py-2 rounded-lg bg-cinema-500 text-white text-sm font-medium hover:bg-cinema-600 transition-colors"
            >
              Browse Popular Movies
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
