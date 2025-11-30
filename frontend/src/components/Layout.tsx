import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Film, Search, MessageCircle, Home } from 'lucide-react'
import { motion } from 'framer-motion'
import clsx from 'clsx'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Home', icon: Home },
    { path: '/search', label: 'Search', icon: Search },
    { path: '/chat', label: 'Chat', icon: MessageCircle },
  ]

  return (
    <div className="min-h-screen flex flex-col">
      {/* Navigation */}
      <header className="sticky top-0 z-50 glass border-b border-slate-700/50">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cinema-500 to-cinema-600 flex items-center justify-center shadow-lg glow-cinema-subtle group-hover:glow-cinema transition-shadow">
                <Film className="w-5 h-5 text-white" />
              </div>
              <span className="font-display text-xl font-bold bg-gradient-to-r from-cinema-400 to-cinema-500 bg-clip-text text-transparent">
                MovieRec
              </span>
            </Link>

            {/* Nav Links */}
            <div className="flex items-center gap-1">
              {navItems.map((item) => {
                const Icon = item.icon
                const isActive = location.pathname === item.path
                
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={clsx(
                      'relative px-4 py-2 rounded-lg flex items-center gap-2 transition-all duration-200',
                      isActive
                        ? 'text-cinema-400'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="font-medium text-sm">{item.label}</span>
                    {isActive && (
                      <motion.div
                        layoutId="activeNav"
                        className="absolute inset-0 bg-cinema-500/10 rounded-lg border border-cinema-500/20"
                        transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                      />
                    )}
                  </Link>
                )
              })}
            </div>
          </div>
        </nav>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer className="glass border-t border-slate-700/50 py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-slate-500 text-sm">
              Powered by Neo4j, KGNN & RAG
            </p>
            <div className="flex items-center gap-4 text-sm text-slate-500">
              <span>Movie Recommendation System</span>
              <span className="w-1 h-1 rounded-full bg-slate-600" />
              <span>v1.0.0</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

