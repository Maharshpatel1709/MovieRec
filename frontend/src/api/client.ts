import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface Movie {
  movie_id: number
  title: string
  overview?: string
  genres: string[]
  release_year?: number
  poster_path?: string
  vote_average?: number
  popularity?: number
  score?: number
  explanation?: string
}

export interface SearchResult {
  movie_id: number
  title: string
  similarity_score: number
  genres: string[]
  overview?: string
  release_year?: number
  poster_path?: string
  vote_average?: number
}

export interface RecommendationResponse {
  recommendations: Movie[]
  method: string
  total: number
}

export interface SearchResponse {
  results: SearchResult[]
  query: string
  total: number
  search_type: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface GraphNode {
  id: string
  label: string
  type: string
  color: string
}

export interface GraphEdge {
  from: string
  to: string
  label: string
}

export interface ReasoningStep {
  step: number
  name: string
  description: string
  result: Record<string, unknown>
}

export interface Reasoning {
  steps: ReasoningStep[]
  graph_traversal?: {
    nodes: GraphNode[]
    edges: GraphEdge[]
    cypher_query: string
  }
  similarity_search?: {
    source_movie: string
    method: string
    scoring: string
  }
  gemini_analysis?: {
    model: string
    parsed_type?: string
    query_type?: string
    entities?: Record<string, unknown>
    reason?: string
  }
  summary: string
  total_time_ms: number
}

export interface ChatResponse {
  message: string
  recommendations: Movie[]
  suggestions: string[]
  metadata?: Record<string, unknown>
  reasoning?: Reasoning
}

export interface RAGResponse {
  query: string
  answer: string
  recommendations: Movie[]
  retrieved_context: Array<{
    movie_id: number
    title: string
    relevance_score: number
    snippet: string
  }>
  reasoning?: string
}

export interface SimilarMovie {
  movie_id: number
  title: string
  overview?: string
  release_year?: number
  vote_average?: number
  poster_path?: string
  genres: string[]
  similarity_score: number
  match_reason?: string
}

export interface MovieDetail {
  movie_id: number
  title: string
  original_title?: string
  overview?: string
  release_date?: string
  release_year?: number
  runtime?: number
  budget?: number
  revenue?: number
  vote_average?: number
  vote_count?: number
  popularity?: number
  poster_path?: string
  backdrop_path?: string
  genres: string[]
  cast: Array<{
    id: number
    name: string
    character?: string
  }>
  directors: Array<{
    id: number
    name: string
  }>
  similar_movies: SimilarMovie[]
}

// API Functions
export const recommendationApi = {
  getHybrid: async (params: {
    user_id?: number
    movie_ids?: number[]
    genres?: string[]
    n_recommendations?: number
  }): Promise<RecommendationResponse> => {
    const response = await api.post('/recommend/hybrid', params)
    return response.data
  },

  getKGNN: async (params: {
    movie_ids?: number[]
    n_recommendations?: number
  }): Promise<RecommendationResponse> => {
    const response = await api.post('/recommend/kgnn', params)
    return response.data
  },

  getSimilar: async (movieId: number, limit = 10): Promise<RecommendationResponse> => {
    const response = await api.get(`/recommend/similar/${movieId}?n_recommendations=${limit}`)
    return response.data
  },

  getPopular: async (genre?: string, limit = 10): Promise<RecommendationResponse> => {
    const params = new URLSearchParams()
    params.append('n_recommendations', limit.toString())
    if (genre) params.append('genre', genre)
    const response = await api.get(`/recommend/popular?${params}`)
    return response.data
  },
}

export interface SmartSearchResponse extends SearchResponse {
  detected_entities?: {
    director?: string
    actor?: string
    genres?: string[]
    similar_to?: string
    decade?: number[]
  }
}

export const searchApi = {
  smart: async (query: string, limit = 20): Promise<SmartSearchResponse> => {
    const response = await api.get(`/search/smart?query=${encodeURIComponent(query)}&limit=${limit}`)
    return response.data
  },

  movies: async (params: {
    query?: string
    genres?: string
    year_min?: number
    year_max?: number
    rating_min?: number
    limit?: number
  }): Promise<SearchResponse> => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.append(key, value.toString())
    })
    const response = await api.get(`/search/movies?${searchParams}`)
    return response.data
  },

  explore: async (category: string, limit = 20): Promise<SearchResponse> => {
    const response = await api.get(`/search/explore?category=${category}&limit=${limit}`)
    return response.data
  },

  suggestions: async (query: string): Promise<{ suggestions: { movie_id: number; title: string; release_year: number }[] }> => {
    const response = await api.get(`/search/suggestions?query=${encodeURIComponent(query)}`)
    return response.data
  },

  getGenres: async (): Promise<{ genres: string[] }> => {
    const response = await api.get('/search/genres')
    return response.data
  },
}

export const ragApi = {
  query: async (query: string, contextLimit = 5): Promise<RAGResponse> => {
    const response = await api.post('/rag/query', {
      query,
      context_limit: contextLimit,
      include_reasoning: true,
    })
    return response.data
  },

  chat: async (message: string, history: ChatMessage[]): Promise<ChatResponse> => {
    const response = await api.post('/rag/chat', {
      message,
      history,
      context_limit: 5,
    })
    return response.data
  },

  explain: async (movieId: number): Promise<{
    movie_id: number
    explanation: string
    key_features: string[]
    similar_movies: Movie[]
  }> => {
    const response = await api.get(`/rag/explain/${movieId}`)
    return response.data
  },
}

export const metadataApi = {
  getMovie: async (movieId: number, includeSimilar = true, similarLimit = 6): Promise<MovieDetail> => {
    const params = new URLSearchParams()
    params.append('include_similar', includeSimilar.toString())
    params.append('similar_limit', similarLimit.toString())
    const response = await api.get(`/metadata/movie/${movieId}?${params}`)
    return response.data
  },

  getStats: async (): Promise<{
    movies: number
    actors: number
    directors: number
    genres: number
  }> => {
    const response = await api.get('/metadata/stats')
    return response.data
  },
}

export const healthApi = {
  check: async (): Promise<{
    status: string
    timestamp: string
    services: Record<string, unknown>
  }> => {
    const response = await api.get('/health')
    return response.data
  },
}

