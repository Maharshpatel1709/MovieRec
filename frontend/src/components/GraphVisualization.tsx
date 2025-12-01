import { useState, useEffect, useRef, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import type { Movie, Reasoning } from '../api/client'

interface GraphNode {
  id: string
  label: string
  type: 'Movie' | 'Genre' | 'Actor' | 'Director' | 'Source'
  x?: number
  y?: number
}

interface GraphEdge {
  source: string
  target: string
  label: string
}

interface GraphVisualizationProps {
  reasoning: Reasoning
  recommendations?: Movie[]
}

const NODE_COLORS: Record<string, string> = {
  Source: '#f59e0b',  // amber - source movie
  Movie: '#6366f1',   // indigo - result movies
  Genre: '#22c55e',   // green
  Actor: '#ec4899',   // pink
  Director: '#3b82f6', // blue
}

const NODE_RADIUS = 28

export function GraphVisualization({ reasoning, recommendations }: GraphVisualizationProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[], edges: GraphEdge[] } | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  // Build graph data from reasoning and recommendations
  useEffect(() => {
    const timer = setTimeout(() => {
      const data = buildGraphData(reasoning, recommendations)
      setGraphData(data)
      setIsLoading(false)
    }, 100) // Small delay to not block UI

    return () => clearTimeout(timer)
  }, [reasoning, recommendations])

  // Calculate positions using a radial layout
  const positionedNodes = useMemo(() => {
    if (!graphData) return []
    
    const width = 600
    const height = 400
    const centerX = width / 2
    const centerY = height / 2
    
    const nodes = [...graphData.nodes]
    const sourceNode = nodes.find(n => n.type === 'Source')
    const otherNodes = nodes.filter(n => n.type !== 'Source')
    
    // Group nodes by type
    const movieNodes = otherNodes.filter(n => n.type === 'Movie')
    const genreNodes = otherNodes.filter(n => n.type === 'Genre')
    const actorNodes = otherNodes.filter(n => n.type === 'Actor')
    const directorNodes = otherNodes.filter(n => n.type === 'Director')
    
    const positioned: GraphNode[] = []
    
    // Source at center
    if (sourceNode) {
      positioned.push({ ...sourceNode, x: centerX, y: centerY })
    }
    
    // Movies in inner ring
    const innerRadius = 100
    movieNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(movieNodes.length, 1) - Math.PI / 2
      positioned.push({
        ...node,
        x: centerX + innerRadius * Math.cos(angle),
        y: centerY + innerRadius * Math.sin(angle)
      })
    })
    
    // Genres, actors, directors in outer ring
    const outerNodes = [...genreNodes, ...actorNodes, ...directorNodes]
    const outerRadius = 170
    outerNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(outerNodes.length, 1) - Math.PI / 2
      positioned.push({
        ...node,
        x: centerX + outerRadius * Math.cos(angle),
        y: centerY + outerRadius * Math.sin(angle)
      })
    })
    
    return positioned
  }, [graphData])

  if (isLoading) {
    return (
      <div className="w-full h-64 flex items-center justify-center bg-slate-900/50 rounded-xl">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="w-6 h-6 text-cinema-400 animate-spin" />
          <span className="text-xs text-slate-400">Building graph...</span>
        </div>
      </div>
    )
  }

  if (!graphData || positionedNodes.length === 0) {
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="w-full bg-slate-900/50 rounded-xl overflow-hidden"
    >
      {/* Graph */}
      <div className="relative overflow-hidden" style={{ height: '400px' }}>
        <svg
          ref={svgRef}
          viewBox="0 0 600 400"
          className="w-full h-full"
          style={{ background: 'radial-gradient(circle at center, rgba(30, 41, 59, 0.5) 0%, transparent 70%)' }}
        >
          {/* Edges */}
          {graphData.edges.map((edge, i) => {
            const source = positionedNodes.find(n => n.id === edge.source)
            const target = positionedNodes.find(n => n.id === edge.target)
            if (!source?.x || !target?.x) return null
            
            return (
              <g key={i}>
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke="rgba(148, 163, 184, 0.3)"
                  strokeWidth="1"
                />
              </g>
            )
          })}
          
          {/* Nodes */}
          {positionedNodes.map((node) => (
            <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
              <motion.circle
                r={NODE_RADIUS}
                fill={NODE_COLORS[node.type] || '#64748b'}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', delay: Math.random() * 0.3 }}
                className="drop-shadow-lg"
              />
              <text
                y={4}
                textAnchor="middle"
                className="fill-white text-[10px] font-semibold pointer-events-none"
              >
                {node.type[0]}
              </text>
              <text
                y={NODE_RADIUS + 14}
                textAnchor="middle"
                className="fill-slate-300 text-[9px] pointer-events-none"
              >
                {truncate(node.label, 12)}
              </text>
            </g>
          ))}
        </svg>
      </div>
      
      {/* Legend */}
      <div className="px-4 py-3 border-t border-slate-700/50 flex flex-wrap justify-center gap-4">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div 
              className="w-3 h-3 rounded-full" 
              style={{ backgroundColor: color }}
            />
            <span className="text-[10px] text-slate-400">{type}</span>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

function buildGraphData(reasoning: Reasoning, recommendations?: Movie[]): { nodes: GraphNode[], edges: GraphEdge[] } {
  const nodes: GraphNode[] = []
  const edges: GraphEdge[] = []
  const addedNodes = new Set<string>()
  
  // Get source movie from similarity search
  const sourceMovie = reasoning.similarity_search?.source_movie
  if (sourceMovie) {
    nodes.push({ id: 'source', label: sourceMovie, type: 'Source' })
    addedNodes.add('source')
  }
  
  // Add recommended movies
  const movies = recommendations?.slice(0, 5) || []
  movies.forEach((movie, i) => {
    const movieId = `movie_${i}`
    if (!addedNodes.has(movieId)) {
      nodes.push({ id: movieId, label: movie.title, type: 'Movie' })
      addedNodes.add(movieId)
      
      // Connect to source if exists
      if (sourceMovie) {
        edges.push({ source: 'source', target: movieId, label: 'SIMILAR_TO' })
      }
      
      // Add genres
      movie.genres?.slice(0, 2).forEach((genre, gi) => {
        const genreId = `genre_${genre.toLowerCase().replace(/\s/g, '_')}`
        if (!addedNodes.has(genreId)) {
          nodes.push({ id: genreId, label: genre, type: 'Genre' })
          addedNodes.add(genreId)
        }
        edges.push({ source: movieId, target: genreId, label: 'HAS_GENRE' })
      })
    }
  })
  
  // Add entities from Gemini analysis
  const entities = reasoning.gemini_analysis?.entities
  if (entities) {
    // Add director
    if (entities.director && typeof entities.director === 'string') {
      const directorId = `director_${entities.director.toLowerCase().replace(/\s/g, '_')}`
      if (!addedNodes.has(directorId)) {
        nodes.push({ id: directorId, label: entities.director, type: 'Director' })
        addedNodes.add(directorId)
        // Connect to movies
        movies.forEach((_, i) => {
          edges.push({ source: `movie_${i}`, target: directorId, label: 'DIRECTED_BY' })
        })
      }
    }
    
    // Add actor
    if (entities.actor && typeof entities.actor === 'string') {
      const actorId = `actor_${entities.actor.toLowerCase().replace(/\s/g, '_')}`
      if (!addedNodes.has(actorId)) {
        nodes.push({ id: actorId, label: entities.actor, type: 'Actor' })
        addedNodes.add(actorId)
        // Connect to movies
        movies.forEach((_, i) => {
          edges.push({ source: actorId, target: `movie_${i}`, label: 'ACTED_IN' })
        })
      }
    }
    
    // Add genres from entities
    if (entities.genres && Array.isArray(entities.genres)) {
      entities.genres.slice(0, 3).forEach((genre: string) => {
        const genreId = `genre_${genre.toLowerCase().replace(/\s/g, '_')}`
        if (!addedNodes.has(genreId)) {
          nodes.push({ id: genreId, label: genre, type: 'Genre' })
          addedNodes.add(genreId)
        }
      })
    }
    
    // Add mood genres
    if (entities.mood_genres && Array.isArray(entities.mood_genres)) {
      entities.mood_genres.slice(0, 3).forEach((genre: string) => {
        const genreId = `genre_${genre.toLowerCase().replace(/\s/g, '_')}`
        if (!addedNodes.has(genreId)) {
          nodes.push({ id: genreId, label: genre, type: 'Genre' })
          addedNodes.add(genreId)
        }
      })
    }
  }
  
  return { nodes, edges }
}

function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str
  return str.slice(0, maxLen - 2) + '...'
}

