"""
Neo4j database service for graph operations.
"""
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from loguru import logger
import numpy as np

from backend.config import settings


class Neo4jService:
    """Service for Neo4j database operations."""
    
    def __init__(self):
        self._driver = None
    
    def connect(self):
        """Establish connection to Neo4j database."""
        try:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            # Verify connection
            self._driver.verify_connectivity()
            logger.info("Connected to Neo4j database")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")
    
    def health_check(self) -> bool:
        """Check if Neo4j connection is healthy."""
        if not self._driver:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False
    
    def _get_session(self):
        """Get a new Neo4j session."""
        if not self._driver:
            self.connect()
        return self._driver.session()
    
    def vector_search(
        self,
        embedding: List[float],
        limit: int = 10,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search on movie embeddings.
        """
        query = """
        CALL db.index.vector.queryNodes('movie_embeddings', $limit, $embedding)
        YIELD node, score
        WHERE score >= $min_score
        RETURN 
            node.movie_id as movie_id,
            node.title as title,
            score,
            node.overview as overview,
            node.release_year as release_year,
            node.poster_path as poster_path,
            node.vote_average as vote_average,
            [(node)-[:HAS_GENRE]->(g:Genre) | g.name] as genres
        """
        
        try:
            with self._get_session() as session:
                result = session.run(
                    query,
                    embedding=embedding,
                    limit=limit,
                    min_score=min_score
                )
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            # Return fallback results if vector index doesn't exist
            return self._fallback_search(limit)
    
    def _fallback_search(self, limit: int) -> List[Dict[str, Any]]:
        """Fallback search when vector index is not available."""
        query = """
        MATCH (m:Movie)
        WHERE m.vote_average IS NOT NULL
        RETURN 
            m.movie_id as movie_id,
            m.title as title,
            1.0 as score,
            m.overview as overview,
            m.release_year as release_year,
            m.poster_path as poster_path,
            m.vote_average as vote_average,
            [(m)-[:HAS_GENRE]->(g:Genre) | g.name] as genres
        ORDER BY m.popularity DESC
        LIMIT $limit
        """
        
        try:
            with self._get_session() as session:
                result = session.run(query, limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Fallback search error: {e}")
            return []
    
    def search_movies(
        self,
        query: str = "",
        genres: Optional[List[str]] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        rating_min: Optional[float] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search movies with text query and filters.
        Optimized for fast retrieval.
        """
        conditions = ["m.popularity IS NOT NULL"]  # Ensure we have popularity for sorting
        params = {"limit": limit, "offset": offset}
        
        if query:
            conditions.append("toLower(m.title) CONTAINS toLower($query)")
            params["query"] = query
        
        if year_min:
            conditions.append("m.release_year >= $year_min")
            params["year_min"] = year_min
        
        if year_max:
            conditions.append("m.release_year <= $year_max")
            params["year_max"] = year_max
        
        if rating_min:
            conditions.append("m.vote_average >= $rating_min")
            params["rating_min"] = rating_min
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        if genres:
            # Genre filter - use optimized pattern
            cypher = f"""
            MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
            WHERE g.name IN $genres
            {where_clause.replace("WHERE", "AND")}
            WITH DISTINCT m
            ORDER BY m.popularity DESC
            SKIP $offset
            LIMIT $limit
            OPTIONAL MATCH (m)-[:HAS_GENRE]->(genre:Genre)
            RETURN 
                m.movie_id as movie_id,
                m.title as title,
                m.overview as overview,
                m.release_year as release_year,
                m.poster_path as poster_path,
                m.vote_average as vote_average,
                m.popularity as popularity,
                collect(DISTINCT genre.name) as genres
            """
            params["genres"] = genres
        else:
            # No genre filter - simple query
            cypher = f"""
            MATCH (m:Movie)
            {where_clause}
            WITH m
            ORDER BY m.popularity DESC
            SKIP $offset
            LIMIT $limit
            OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
            RETURN 
                m.movie_id as movie_id,
                m.title as title,
                m.overview as overview,
                m.release_year as release_year,
                m.poster_path as poster_path,
                m.vote_average as vote_average,
                m.popularity as popularity,
                collect(DISTINCT g.name) as genres
            """
        
        try:
            with self._get_session() as session:
                result = session.run(cypher, **params)
                records = list(result)  # Consume results
                return [dict(record) for record in records]
        except Exception as e:
            logger.error(f"Search movies error: {e}")
            return []
    
    def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed movie information."""
        # Simple query - get movie first
        query = """
        MATCH (m:Movie {movie_id: $movie_id})
        OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
        WITH m, collect(DISTINCT g.name) as genres
        OPTIONAL MATCH (a:Actor)-[:ACTED_IN]->(m)
        WITH m, genres, collect(DISTINCT {id: a.actor_id, name: a.name, character: a.character})[0..10] as cast
        OPTIONAL MATCH (d:Director)-[:DIRECTED]->(m)
        WITH m, genres, cast, collect(DISTINCT {id: d.director_id, name: d.name, job: 'Director'}) as directors
        RETURN 
            m.movie_id as movie_id,
            m.title as title,
            m.original_title as original_title,
            m.overview as overview,
            m.release_date as release_date,
            m.release_year as release_year,
            m.runtime as runtime,
            m.budget as budget,
            m.revenue as revenue,
            m.vote_average as vote_average,
            m.vote_count as vote_count,
            m.popularity as popularity,
            m.poster_path as poster_path,
            m.backdrop_path as backdrop_path,
            genres,
            cast,
            directors
        """
        
        try:
            with self._get_session() as session:
                result = session.run(query, movie_id=movie_id, timeout=10)
                records = list(result)  # Consume the result
                if records:
                    data = dict(records[0])
                    # Clean up cast (remove None entries)
                    data["cast"] = [c for c in data.get("cast", []) if c and c.get("id")]
                    data["directors"] = [d for d in data.get("directors", []) if d and d.get("id")]
                    return data
                return None
        except Exception as e:
            logger.error(f"Get movie details error: {e}")
            return None
    
    def get_actor_details(self, actor_id: int) -> Optional[Dict[str, Any]]:
        """Get actor details with their movies."""
        query = """
        MATCH (a:Actor {actor_id: $actor_id})
        RETURN 
            a.actor_id as id,
            a.name as name,
            a.profile_path as profile_path,
            [(a)-[:ACTED_IN]->(m:Movie) | {
                movie_id: m.movie_id, 
                title: m.title, 
                year: m.release_year,
                poster_path: m.poster_path,
                vote_average: m.vote_average
            }][0..20] as movies
        """
        
        try:
            with self._get_session() as session:
                result = session.run(query, actor_id=actor_id)
                record = result.single()
                if record:
                    data = dict(record)
                    data["movies"] = [m for m in data["movies"] if m.get("movie_id")]
                    # Get genres from movies
                    data["known_for_genres"] = []
                    return data
                return None
        except Exception as e:
            logger.error(f"Get actor details error: {e}")
            return None
    
    def get_director_details(self, director_id: int) -> Optional[Dict[str, Any]]:
        """Get director details with their movies."""
        query = """
        MATCH (d:Director {director_id: $director_id})
        OPTIONAL MATCH (d)-[:DIRECTED]->(m:Movie)
        WITH d, collect({
            movie_id: m.movie_id, 
            title: m.title, 
            year: m.release_year,
            vote_average: m.vote_average,
            poster_path: m.poster_path
        }) as movies,
        avg(m.vote_average) as avg_rating
        RETURN 
            d.director_id as id,
            d.name as name,
            d.profile_path as profile_path,
            movies,
            avg_rating as average_rating
        """
        
        try:
            with self._get_session() as session:
                result = session.run(query, director_id=director_id)
                record = result.single()
                if record:
                    data = dict(record)
                    data["movies"] = [m for m in data["movies"] if m.get("movie_id")]
                    return data
                return None
        except Exception as e:
            logger.error(f"Get director details error: {e}")
            return None
    
    def get_all_genres(self) -> List[str]:
        """Get all available genres."""
        query = """
        MATCH (g:Genre)
        RETURN g.name as name
        ORDER BY g.name
        """
        
        try:
            with self._get_session() as session:
                result = session.run(query)
                return [record["name"] for record in result]
        except Exception as e:
            logger.error(f"Get genres error: {e}")
            # Return default genres if database is not available
            return [
                "Action", "Adventure", "Animation", "Comedy", "Crime",
                "Documentary", "Drama", "Family", "Fantasy", "History",
                "Horror", "Music", "Mystery", "Romance", "Science Fiction",
                "TV Movie", "Thriller", "War", "Western"
            ]
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        query = """
        MATCH (m:Movie) WITH count(m) as movies
        MATCH (a:Actor) WITH movies, count(a) as actors
        MATCH (d:Director) WITH movies, actors, count(d) as directors
        MATCH (g:Genre) WITH movies, actors, directors, count(g) as genres
        RETURN movies, actors, directors, genres
        """
        
        try:
            with self._get_session() as session:
                result = session.run(query)
                record = result.single()
                if record:
                    return dict(record)
                return {"movies": 0, "actors": 0, "directors": 0, "genres": 0}
        except Exception as e:
            logger.error(f"Get stats error: {e}")
            return {"movies": 0, "actors": 0, "directors": 0, "genres": 0}
    
    def get_graph_edges(self) -> Dict[str, Any]:
        """Extract graph edges for KGNN training."""
        queries = {
            "movie_genre": """
                MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
                RETURN m.movie_id as source, g.name as target, 'HAS_GENRE' as type
            """,
            "actor_movie": """
                MATCH (a:Actor)-[:ACTED_IN]->(m:Movie)
                RETURN a.actor_id as source, m.movie_id as target, 'ACTED_IN' as type
            """,
            "director_movie": """
                MATCH (d:Director)-[:DIRECTED]->(m:Movie)
                RETURN d.director_id as source, m.movie_id as target, 'DIRECTED' as type
            """
        }
        
        edges = {"movie_genre": [], "actor_movie": [], "director_movie": []}
        
        try:
            with self._get_session() as session:
                for edge_type, query in queries.items():
                    result = session.run(query)
                    edges[edge_type] = [dict(record) for record in result]
            return edges
        except Exception as e:
            logger.error(f"Get graph edges error: {e}")
            return edges
    
    def get_movie_embeddings(self) -> Dict[int, List[float]]:
        """Get all movie embeddings for KGNN."""
        query = """
        MATCH (m:Movie)
        WHERE m.embedding IS NOT NULL
        RETURN m.movie_id as movie_id, m.embedding as embedding
        """
        
        try:
            with self._get_session() as session:
                result = session.run(query)
                return {record["movie_id"]: record["embedding"] for record in result}
        except Exception as e:
            logger.error(f"Get movie embeddings error: {e}")
            return {}
    
    def get_title_suggestions(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Get movie title suggestions for autocomplete."""
        cypher = """
        MATCH (m:Movie)
        WHERE m.title =~ $pattern
        RETURN 
            m.movie_id as movie_id,
            m.title as title,
            m.release_year as release_year,
            m.vote_average as vote_average
        ORDER BY m.popularity DESC
        LIMIT $limit
        """
        
        try:
            with self._get_session() as session:
                result = session.run(cypher, pattern=f"(?i).*{query}.*", limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Title suggestions error: {e}")
            return []


# Singleton instance
neo4j_service = Neo4jService()

