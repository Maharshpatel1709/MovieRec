# 🎬 MovieRec - Movie Recommendation System

## System Overview

MovieRec is a movie recommendation system built with a **FastAPI backend**, **Neo4j graph database**, and **Google Gemini LLM** for intelligent query understanding. The system follows a service-oriented architecture where the API layer delegates to specialized services that handle different aspects of the recommendation pipeline.

## Core Architecture

The backend is structured into three main layers: **API Routes**, **Services**, and **Data/Models**. The FastAPI application (`main.py`) initializes connections to Neo4j and loads ML models at startup, then routes incoming requests to five endpoint groups: `/health` for system status, `/rag` for chat-based interactions, `/search` for query-based movie discovery, `/recommend` for traditional recommendations, and `/metadata` for movie/actor/director details.

The heart of the system is the **SmartRAGService**, which orchestrates all chat and search queries. When a user sends a message like "Movies directed by Cristopher Nolan", the service first checks a 5-minute response cache for efficiency. If not cached, it forwards the query to the **GeminiQueryService**, which calls Google's Gemini 1.5 Flash API with a carefully crafted prompt. The prompt instructs Gemini to not only classify the query intent (director/actor/genre/similar/unsupported) but also to **correct typos** in names and titles—so "Cristopher" becomes "Christopher Nolan" automatically. If Gemini is unavailable, a fallback rule-based parser with a typo correction dictionary handles common cases.

Based on the parsed query type, SmartRAGService routes to the appropriate method in **GraphQueryService**, which constructs and executes Cypher queries against Neo4j. For director queries, it matches `(d:Director)-[:DIRECTED]->(m:Movie)` with case-insensitive regex patterns. For "movies like X" queries, it performs multi-hop graph traversal, scoring candidates by shared genres (5x weight), shared actors (3x), same director (2x), and same decade (1x). The **Neo4jService** provides low-level database operations including connection management, health checks, and optimized queries that use pattern comprehensions to avoid Cartesian products.

## Graph Schema and Data Flow

The Neo4j knowledge graph stores four node types—**Movie**, **Actor**, **Director**, and **Genre**—connected by three relationship types: `ACTED_IN`, `DIRECTED`, and `HAS_GENRE`. Movies contain properties like `movie_id`, `title`, `overview`, `release_year`, `vote_average`, `popularity`, and `poster_path`. This structure enables efficient traversal queries for finding related content through shared relationships.

For the movie detail page, the system demonstrates an optimization pattern: instead of making two sequential API calls (one for movie metadata, one for similar movies), the `/metadata/movie/{id}` endpoint runs both queries **in parallel** using a ThreadPoolExecutor, combines the results, and returns them in a single response. This cuts page load time roughly in half.

## Query Classification and Handling

The GeminiQueryService classifies queries into supported types (director, actor, genre, year, similar, combined, mood-based like "feel-good movies") and unsupported types (plot-based like "twist endings", or subjective like "underrated gems"). For unsupported queries, it returns a helpful message explaining what the system can search for instead, rather than returning poor results. This graceful degradation improves user experience.

## ML Models (Fallback Layer)

The `models/` directory contains traditional recommendation algorithms—**Content-Based Filtering** (TF-IDF on movie text), **Collaborative Filtering** (SVD), a **Hybrid** combiner, and a **KGNN** (Knowledge Graph Neural Network). These are loaded by the ModelService at startup but currently serve as fallbacks since the graph-based approach provides more accurate results for the available data. The model architecture is preserved for future enhancement when user rating data becomes available.

## Performance Considerations

The system implements several optimizations: response caching with TTL, parallel query execution via thread pools, typo correction at the LLM layer (avoiding multiple failed DB lookups), fuzzy regex matching in Cypher queries, and query restructuring to fetch results before performing expensive operations like genre collection. The frontend communicates via a single consolidated API call per page where possible, minimizing network round trips.
