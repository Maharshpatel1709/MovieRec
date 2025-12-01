import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import ForceGraph2D from 'react-force-graph-2d'
import type { Movie, Reasoning } from '../api/client'

interface GraphNode {
  id: string
  label: string
  type: 'Movie' | 'Genre' | 'Actor' | 'Director' | 'Source'
  group?: number
}

interface GraphLink {
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

export function GraphVisualization({ reasoning, recommendations }: GraphVisualizationProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[], links: GraphLink[] } | null>(null)

  // Build graph data from reasoning and recommendations
  useEffect(() => {
    const timer = setTimeout(() => {
      const data = buildGraphData(reasoning, recommendations)
      setGraphData(data)
      setIsLoading(false)
    }, 100) // Small delay to not block UI

    return () => clearTimeout(timer)
  }, [reasoning, recommendations])

  if (isLoading) {
    return (
      <div className="w-full h-96 flex items-center justify-center bg-slate-900/50 rounded-xl">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="w-6 h-6 text-cinema-400 animate-spin" />
          <span className="text-xs text-slate-400">Building graph...</span>
        </div>
      </div>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="w-full bg-slate-900/50 rounded-xl overflow-hidden"
    >
      {/* Graph */}
      <div className="relative" style={{ height: '500px' }}>
        <ForceGraph2D
          graphData={graphData}
          nodeLabel={(node: GraphNode) => `${node.label} (${node.type})`}
          nodeColor={(node: GraphNode) => NODE_COLORS[node.type] || '#64748b'}
          nodeVal={(node: GraphNode) => {
            // Size based on type
            if (node.type === 'Source') return 12
            if (node.type === 'Movie') return 10
            return 8
          }}
          linkLabel={(link: GraphLink) => link.label}
          linkColor={() => 'rgba(148, 163, 184, 0.4)'}
          linkWidth={1.5}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          backgroundColor="rgba(15, 23, 42, 0.5)"
          nodeCanvasObject={(node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const label = node.label
            const fontSize = 12 / globalScale
            ctx.font = `${fontSize}px Sans-Serif`
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.fillStyle = '#ffffff'
            ctx.fillText(label, node.x || 0, (node.y || 0) + 20)
          }}
          onNodeDragEnd={(node: GraphNode) => {
            node.fx = node.x
            node.fy = node.y
          }}
          onNodeClick={(node: GraphNode) => {
            // Pin/unpin node on click
            if (node.fx !== undefined && node.fy !== undefined) {
              node.fx = undefined
              node.fy = undefined
            } else {
              node.fx = node.x
              node.fy = node.y
            }
          }}
        />
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

function buildGraphData(reasoning: Reasoning, recommendations?: Movie[]): { nodes: GraphNode[], links: GraphLink[] } {
  const nodes: GraphNode[] = []
  const links: GraphLink[] = []
  const nodeMap = new Map<string, GraphNode>()
  
  // Collect all movies (source + recommendations)
  const allMovies: Array<{ id: string, title: string, genres?: string[], actors?: string[], directors?: string[] }> = []
  
  // Add source movie if exists
  const sourceMovie = reasoning.similarity_search?.source_movie
  if (sourceMovie) {
    // Try to get source movie details from recommendations or reasoning
    const sourceMovieData = recommendations?.find(m => 
      m.title.toLowerCase().includes(sourceMovie.toLowerCase()) ||
      sourceMovie.toLowerCase().includes(m.title.toLowerCase())
    )
    
    allMovies.push({
      id: 'source',
      title: sourceMovie,
      genres: sourceMovieData?.genres || [],
      actors: [], // We don't have actor data for source in current structure
      directors: [] // We don't have director data for source in current structure
    })
  }
  
  // Add recommended movies
  const movies = recommendations?.slice(0, 10) || []
  movies.forEach((movie, i) => {
    allMovies.push({
      id: `movie_${i}`,
      title: movie.title,
      genres: movie.genres || [],
      actors: [], // We don't have actor data in Movie type currently
      directors: [] // We don't have director data in Movie type currently
    })
  })
  
  // Add movie nodes
  allMovies.forEach(movie => {
    if (!nodeMap.has(movie.id)) {
      const node: GraphNode = {
        id: movie.id,
        label: movie.title,
        type: movie.id === 'source' ? 'Source' : 'Movie'
      }
      nodes.push(node)
      nodeMap.set(movie.id, node)
    }
  })
  
  // Count genres across all movies (including source)
  const genreCount = new Map<string, number>()
  const genreToMovies = new Map<string, string[]>()
  
  allMovies.forEach(movie => {
    movie.genres?.forEach(genre => {
      const genreKey = genre.toLowerCase().trim()
      genreCount.set(genreKey, (genreCount.get(genreKey) || 0) + 1)
      
      if (!genreToMovies.has(genreKey)) {
        genreToMovies.set(genreKey, [])
      }
      genreToMovies.get(genreKey)!.push(movie.id)
    })
  })
  
  // Only add genres that appear in 2+ movies (including source)
  genreCount.forEach((count, genreKey) => {
    if (count >= 2) {
      const genreLabel = genreToMovies.get(genreKey)?.[0] ? 
        allMovies.find(m => m.id === genreToMovies.get(genreKey)![0])?.genres?.find(g => g.toLowerCase().trim() === genreKey) || genreKey :
        genreKey
      
      const genreId = `genre_${genreKey.replace(/\s/g, '_')}`
      if (!nodeMap.has(genreId)) {
        const node: GraphNode = {
          id: genreId,
          label: genreLabel,
          type: 'Genre'
        }
        nodes.push(node)
        nodeMap.set(genreId, node)
        
        // Connect to all movies that have this genre
        genreToMovies.get(genreKey)!.forEach(movieId => {
          links.push({
            source: movieId,
            target: genreId,
            label: 'HAS_GENRE'
          })
        })
      }
    }
  })
  
  // Parse match_reason to extract shared actors/directors
  // Format: "X shared actors: Name1, Name2; same director: Name"
  const actorCount = new Map<string, number>()
  const directorCount = new Map<string, number>()
  const actorToMovies = new Map<string, string[]>()
  const directorToMovies = new Map<string, string[]>()
  
  // Process all movies (including source if it exists)
  const allMovieIds = allMovies.map(m => m.id)
  
  movies.forEach((movie, i) => {
    const movieId = `movie_${i}`
    const matchReason = (movie as any).match_reason || ''
    
    // Parse "X shared actors: Name1, Name2"
    const actorMatch = matchReason.match(/(\d+)\s+shared\s+actors?:\s*([^;]+)/i)
    if (actorMatch) {
      const actorNames = actorMatch[2].split(',').map(a => a.trim())
      actorNames.forEach(actorName => {
        const actorKey = actorName.toLowerCase().trim()
        const currentCount = actorCount.get(actorKey) || 0
        actorCount.set(actorKey, currentCount + 1)
        
        if (!actorToMovies.has(actorKey)) {
          actorToMovies.set(actorKey, [])
        }
        actorToMovies.get(actorKey)!.push(movieId)
        
        // If source exists, also count it (shared actors means source + this movie)
        if (sourceMovie && !actorToMovies.get(actorKey)!.includes('source')) {
          actorCount.set(actorKey, actorCount.get(actorKey)! + 1)
          actorToMovies.get(actorKey)!.push('source')
        }
      })
    }
    
    // Parse "same director: Name"
    const directorMatch = matchReason.match(/same\s+director:\s*([^;]+)/i)
    if (directorMatch) {
      const directorName = directorMatch[1].trim()
      const directorKey = directorName.toLowerCase().trim()
      const currentCount = directorCount.get(directorKey) || 0
      directorCount.set(directorKey, currentCount + 1)
      
      if (!directorToMovies.has(directorKey)) {
        directorToMovies.set(directorKey, [])
      }
      directorToMovies.get(directorKey)!.push(movieId)
      
      // If source exists, also count it
      if (sourceMovie && !directorToMovies.get(directorKey)!.includes('source')) {
        directorCount.set(directorKey, directorCount.get(directorKey)! + 1)
        directorToMovies.get(directorKey)!.push('source')
      }
    }
  })
  
  // Only add actors that appear in 2+ movies (including source)
  actorCount.forEach((count, actorKey) => {
    if (count >= 2) {
      // Capitalize properly
      const actorLabel = actorKey.split(' ').map(w => 
        w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()
      ).join(' ')
      
      const actorId = `actor_${actorKey.replace(/\s/g, '_')}`
      if (!nodeMap.has(actorId)) {
        const node: GraphNode = {
          id: actorId,
          label: actorLabel,
          type: 'Actor'
        }
        nodes.push(node)
        nodeMap.set(actorId, node)
        
        // Connect to all movies that have this actor
        actorToMovies.get(actorKey)!.forEach(movieId => {
          links.push({
            source: actorId,
            target: movieId,
            label: 'ACTED_IN'
          })
        })
      }
    }
  })
  
  // Only add directors that appear in 2+ movies (including source)
  directorCount.forEach((count, directorKey) => {
    if (count >= 2) {
      const directorLabel = directorKey.split(' ').map(w => 
        w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()
      ).join(' ')
      
      const directorId = `director_${directorKey.replace(/\s/g, '_')}`
      if (!nodeMap.has(directorId)) {
        const node: GraphNode = {
          id: directorId,
          label: directorLabel,
          type: 'Director'
        }
        nodes.push(node)
        nodeMap.set(directorId, node)
        
        // Connect to all movies that have this director
        directorToMovies.get(directorKey)!.forEach(movieId => {
          links.push({
            source: directorId,
            target: movieId,
            label: 'DIRECTED'
          })
        })
      }
    }
  })
  
  return { nodes, links }
}
