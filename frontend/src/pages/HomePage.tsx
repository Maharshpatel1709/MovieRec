import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Sparkles, ArrowRight, Film, Users, Cpu, MessageCircle } from 'lucide-react'
import { SearchBar } from '../components/SearchBar'
import { MovieCard, MovieCardSkeleton } from '../components/MovieCard'
import { recommendationApi } from '../api/client'
import type { Movie } from '../api/client'

export function HomePage() {
  const navigate = useNavigate()
  const [popularMovies, setPopularMovies] = useState<Movie[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPopular = async () => {
      try {
        const data = await recommendationApi.getPopular(undefined, 8)
        setPopularMovies(data.recommendations)
      } catch (error) {
        console.error('Failed to fetch popular movies:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchPopular()
  }, [])

  const handleSearch = (query: string) => {
    navigate(`/search?q=${encodeURIComponent(query)}`)
  }

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-cinema-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-midnight-500/20 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-32">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-3xl mx-auto"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass border border-cinema-500/20 text-cinema-400 text-sm mb-8">
              <Sparkles className="w-4 h-4" />
              AI-Powered Movie Discovery
            </div>
            
            <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-bold text-white leading-tight mb-6">
              Find Your Next
              <span className="block bg-gradient-to-r from-cinema-400 via-cinema-500 to-cinema-400 bg-clip-text text-transparent">
                Favorite Movie
              </span>
            </h1>
            
            <p className="text-lg text-slate-400 mb-10 max-w-2xl mx-auto">
              Discover personalized recommendations powered by knowledge graphs, 
              neural networks, and natural language understanding.
            </p>

            {/* Search Bar */}
            <SearchBar
              onSearch={handleSearch}
              placeholder="Describe what you want to watch..."
              size="large"
              className="max-w-2xl mx-auto"
            />
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 border-y border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Film,
                title: 'Smart Recommendations',
                description: 'Hybrid algorithm combining content-based and collaborative filtering for personalized suggestions.',
              },
              {
                icon: Cpu,
                title: 'Graph Neural Networks',
                description: 'KGNN learns relationships between movies, actors, and genres for deeper understanding.',
              },
              {
                icon: MessageCircle,
                title: 'Natural Language Chat',
                description: 'Ask questions in plain English and get intelligent recommendations with explanations.',
              },
            ].map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 + 0.3 }}
                className="glass rounded-2xl p-6 border border-slate-700/50 hover:border-cinema-500/30 transition-colors group"
              >
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cinema-500/20 to-cinema-600/20 flex items-center justify-center mb-4 group-hover:from-cinema-500/30 group-hover:to-cinema-600/30 transition-colors">
                  <feature.icon className="w-6 h-6 text-cinema-400" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-slate-400 text-sm">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Popular Movies Section */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-10">
            <div>
              <h2 className="font-display text-3xl font-bold text-white mb-2">
                Popular Right Now
              </h2>
              <p className="text-slate-400">Trending movies people are watching</p>
            </div>
            <Link
              to="/search"
              className="hidden sm:flex items-center gap-2 text-cinema-400 hover:text-cinema-300 transition-colors"
            >
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {loading
              ? Array.from({ length: 8 }).map((_, i) => <MovieCardSkeleton key={i} />)
              : popularMovies.map((movie, index) => (
                  <MovieCard key={movie.movie_id} movie={movie} index={index} />
                ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="glass rounded-3xl p-8 md:p-12 border border-slate-700/50 text-center relative overflow-hidden">
            {/* Background gradient */}
            <div className="absolute inset-0 bg-gradient-to-br from-cinema-500/10 via-transparent to-midnight-500/10" />
            
            <div className="relative">
              <h2 className="font-display text-3xl md:text-4xl font-bold text-white mb-4">
                Ready to Explore?
              </h2>
              <p className="text-slate-400 mb-8 max-w-xl mx-auto">
                Start a conversation with our AI assistant and discover movies 
                tailored to your mood, preferences, and curiosity.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  to="/chat"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-cinema-500 to-cinema-600 text-white font-medium rounded-xl hover:from-cinema-600 hover:to-cinema-700 transition-all shadow-lg glow-cinema-subtle"
                >
                  <MessageCircle className="w-5 h-5" />
                  Start Chatting
                </Link>
                <Link
                  to="/search"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 glass border border-slate-600 text-white font-medium rounded-xl hover:bg-slate-700/50 transition-all"
                >
                  <Users className="w-5 h-5" />
                  Browse Movies
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

