"""
Graph Query Service
Direct Cypher queries for structured movie searches.
"""
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

from backend.services.neo4j_service import neo4j_service


class GraphQueryService:
    """
    Service for executing structured graph queries.
    Much faster than vector search for specific entity queries.
    """
    
    def search_by_director(
        self,
        director_name: str,
        limit: int = 10,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find movies by a specific director.
        
        Args:
            director_name: Name of the director (partial match supported)
            limit: Maximum results to return
            year_min: Optional minimum year filter
            year_max: Optional maximum year filter
        """
        # Build query with optional filters
        where_clauses = []
        params = {"director_name": f"(?i).*{director_name}.*", "limit": limit}
        
        if year_min:
            where_clauses.append("m.release_year >= $year_min")
            params["year_min"] = year_min
        if year_max:
            where_clauses.append("m.release_year <= $year_max")
            params["year_max"] = year_max
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        query = f"""
        MATCH (d:Director)-[:DIRECTED]->(m:Movie)
        WHERE d.name =~ $director_name
        {where_clause}
        OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
        WITH m, d, collect(DISTINCT g.name) as genres
        RETURN 
            m.movie_id as movie_id,
            m.title as title,
            m.overview as overview,
            m.release_year as release_year,
            m.vote_average as vote_average,
            m.poster_path as poster_path,
            m.popularity as popularity,
            genres,
            d.name as director_name
        ORDER BY m.vote_average DESC, m.popularity DESC
        LIMIT $limit
        """
        
        try:
            with neo4j_service._driver.session() as session:
                result = session.run(query, params)
                movies = [dict(record) for record in result]
                logger.info(f"Found {len(movies)} movies by director '{director_name}'")
                return movies
        except Exception as e:
            logger.error(f"Director search error: {e}")
            return []
    
    def search_by_actor(
        self,
        actor_name: str,
        limit: int = 10,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find movies featuring a specific actor.
        """
        where_clauses = []
        params = {"actor_name": f"(?i).*{actor_name}.*", "limit": limit}
        
        if year_min:
            where_clauses.append("m.release_year >= $year_min")
            params["year_min"] = year_min
        if year_max:
            where_clauses.append("m.release_year <= $year_max")
            params["year_max"] = year_max
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        query = f"""
        MATCH (a:Actor)-[:ACTED_IN]->(m:Movie)
        WHERE a.name =~ $actor_name
        {where_clause}
        OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
        WITH m, a, collect(DISTINCT g.name) as genres
        RETURN 
            m.movie_id as movie_id,
            m.title as title,
            m.overview as overview,
            m.release_year as release_year,
            m.vote_average as vote_average,
            m.poster_path as poster_path,
            m.popularity as popularity,
            genres,
            a.name as actor_name
        ORDER BY m.vote_average DESC, m.popularity DESC
        LIMIT $limit
        """
        
        try:
            with neo4j_service._driver.session() as session:
                result = session.run(query, params)
                movies = [dict(record) for record in result]
                logger.info(f"Found {len(movies)} movies with actor '{actor_name}'")
                return movies
        except Exception as e:
            logger.error(f"Actor search error: {e}")
            return []
    
    def search_by_genre(
        self,
        genres: List[str],
        limit: int = 10,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        rating_min: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Find movies by genre(s).
        """
        where_clauses = ["g.name IN $genres"]
        params = {"genres": genres, "limit": limit}
        
        if year_min:
            where_clauses.append("m.release_year >= $year_min")
            params["year_min"] = year_min
        if year_max:
            where_clauses.append("m.release_year <= $year_max")
            params["year_max"] = year_max
        if rating_min:
            where_clauses.append("m.vote_average >= $rating_min")
            params["rating_min"] = rating_min
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}"
        
        query = f"""
        MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
        {where_clause}
        WITH m, collect(DISTINCT g.name) as genres
        RETURN 
            m.movie_id as movie_id,
            m.title as title,
            m.overview as overview,
            m.release_year as release_year,
            m.vote_average as vote_average,
            m.poster_path as poster_path,
            m.popularity as popularity,
            genres
        ORDER BY m.vote_average DESC, m.popularity DESC
        LIMIT $limit
        """
        
        try:
            with neo4j_service._driver.session() as session:
                result = session.run(query, params)
                movies = [dict(record) for record in result]
                logger.info(f"Found {len(movies)} movies in genres {genres}")
                return movies
        except Exception as e:
            logger.error(f"Genre search error: {e}")
            return []
    
    def search_by_year_range(
        self,
        year_min: int,
        year_max: int,
        genres: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find movies within a year range.
        """
        params = {
            "year_min": year_min,
            "year_max": year_max,
            "limit": limit
        }
        
        if genres:
            query = """
            MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
            WHERE m.release_year >= $year_min 
              AND m.release_year <= $year_max
              AND g.name IN $genres
            WITH m, collect(DISTINCT g.name) as genres
            RETURN 
                m.movie_id as movie_id,
                m.title as title,
                m.overview as overview,
                m.release_year as release_year,
                m.vote_average as vote_average,
                m.poster_path as poster_path,
                m.popularity as popularity,
                genres
            ORDER BY m.vote_average DESC, m.popularity DESC
            LIMIT $limit
            """
            params["genres"] = genres
        else:
            query = """
            MATCH (m:Movie)
            WHERE m.release_year >= $year_min 
              AND m.release_year <= $year_max
            OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
            WITH m, collect(DISTINCT g.name) as genres
            RETURN 
                m.movie_id as movie_id,
                m.title as title,
                m.overview as overview,
                m.release_year as release_year,
                m.vote_average as vote_average,
                m.poster_path as poster_path,
                m.popularity as popularity,
                genres
            ORDER BY m.vote_average DESC, m.popularity DESC
            LIMIT $limit
            """
        
        try:
            with neo4j_service._driver.session() as session:
                result = session.run(query, params)
                movies = [dict(record) for record in result]
                logger.info(f"Found {len(movies)} movies from {year_min}-{year_max}")
                return movies
        except Exception as e:
            logger.error(f"Year range search error: {e}")
            return []
    
    def search_combined(
        self,
        director: Optional[str] = None,
        actor: Optional[str] = None,
        genres: Optional[List[str]] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        rating_min: Optional[float] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Combined search with multiple filters.
        """
        match_clauses = ["MATCH (m:Movie)"]
        where_clauses = []
        params = {"limit": limit}
        
        # Add director match
        if director:
            match_clauses.append("MATCH (d:Director)-[:DIRECTED]->(m)")
            where_clauses.append("d.name =~ $director_pattern")
            params["director_pattern"] = f"(?i).*{director}.*"
        
        # Add actor match
        if actor:
            match_clauses.append("MATCH (a:Actor)-[:ACTED_IN]->(m)")
            where_clauses.append("a.name =~ $actor_pattern")
            params["actor_pattern"] = f"(?i).*{actor}.*"
        
        # Add genre match
        if genres:
            match_clauses.append("MATCH (m)-[:HAS_GENRE]->(g:Genre)")
            where_clauses.append("g.name IN $genres")
            params["genres"] = genres
        
        # Add year filters
        if year_min:
            where_clauses.append("m.release_year >= $year_min")
            params["year_min"] = year_min
        if year_max:
            where_clauses.append("m.release_year <= $year_max")
            params["year_max"] = year_max
        
        # Add rating filter
        if rating_min:
            where_clauses.append("m.vote_average >= $rating_min")
            params["rating_min"] = rating_min
        
        # Build query
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        query = f"""
        {' '.join(match_clauses)}
        {where_clause}
        OPTIONAL MATCH (m)-[:HAS_GENRE]->(genre:Genre)
        OPTIONAL MATCH (dir:Director)-[:DIRECTED]->(m)
        WITH m, collect(DISTINCT genre.name) as genres, collect(DISTINCT dir.name) as directors
        RETURN 
            m.movie_id as movie_id,
            m.title as title,
            m.overview as overview,
            m.release_year as release_year,
            m.vote_average as vote_average,
            m.poster_path as poster_path,
            m.popularity as popularity,
            genres,
            directors
        ORDER BY m.vote_average DESC, m.popularity DESC
        LIMIT $limit
        """
        
        try:
            with neo4j_service._driver.session() as session:
                result = session.run(query, params)
                movies = [dict(record) for record in result]
                logger.info(f"Combined search found {len(movies)} movies")
                return movies
        except Exception as e:
            logger.error(f"Combined search error: {e}")
            return []
    
    def get_related_movies(
        self,
        movie_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find related movies based on shared actors, directors, or genres.
        """
        query = """
        MATCH (m:Movie {movie_id: $movie_id})
        
        // Find movies with same director
        OPTIONAL MATCH (m)<-[:DIRECTED]-(d:Director)-[:DIRECTED]->(related1:Movie)
        WHERE related1.movie_id <> $movie_id
        
        // Find movies with same actors
        OPTIONAL MATCH (m)<-[:ACTED_IN]-(a:Actor)-[:ACTED_IN]->(related2:Movie)
        WHERE related2.movie_id <> $movie_id
        
        // Find movies with same genre
        OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(related3:Movie)
        WHERE related3.movie_id <> $movie_id
        
        WITH collect(DISTINCT related1) + collect(DISTINCT related2) + collect(DISTINCT related3) as allRelated
        UNWIND allRelated as related
        WITH DISTINCT related
        WHERE related IS NOT NULL
        
        OPTIONAL MATCH (related)-[:HAS_GENRE]->(g:Genre)
        WITH related, collect(DISTINCT g.name) as genres
        
        RETURN 
            related.movie_id as movie_id,
            related.title as title,
            related.overview as overview,
            related.release_year as release_year,
            related.vote_average as vote_average,
            related.poster_path as poster_path,
            genres
        ORDER BY related.vote_average DESC
        LIMIT $limit
        """
        
        try:
            with neo4j_service._driver.session() as session:
                result = session.run(query, {"movie_id": movie_id, "limit": limit})
                movies = [dict(record) for record in result]
                logger.info(f"Found {len(movies)} related movies for movie_id={movie_id}")
                return movies
        except Exception as e:
            logger.error(f"Related movies search error: {e}")
            return []
    
    def find_similar_movies(
        self,
        movie_id: int = None,
        movie_title: str = None,
        limit: int = 10,
        genre_weight: float = 5.0,
        actor_weight: float = 3.0,
        director_weight: float = 2.0,
        era_weight: float = 1.0
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Find similar movies using multi-hop graph traversal with weighted scoring.
        
        Priority (customizable weights):
        - Genre matches: highest (5.0) - comedies similar to comedies
        - Actor matches: high (3.0) - same actors often = similar vibe
        - Director matches: medium (2.0) - same director = similar style
        - Time era: low (1.0) - similar decade = similar cultural context
        
        Args:
            movie_id: ID of the source movie
            movie_title: Title to search for (if movie_id not provided)
            limit: Max results to return
            genre_weight: Score per shared genre
            actor_weight: Score per shared actor
            director_weight: Score per shared director
            era_weight: Score for same decade
            
        Returns:
            Tuple of (movies list, similarity_details dict)
        """
        # First, get the source movie
        if movie_id:
            source_query = "MATCH (m:Movie {movie_id: $movie_id}) RETURN m"
            params = {"movie_id": movie_id}
        elif movie_title:
            source_query = "MATCH (m:Movie) WHERE m.title =~ $title_pattern RETURN m LIMIT 1"
            params = {"title_pattern": f"(?i).*{movie_title}.*"}
        else:
            logger.error("Either movie_id or movie_title must be provided")
            return [], {}
        
        # Main similarity query with weighted scoring
        similarity_query = """
        // Get source movie
        MATCH (source:Movie)
        WHERE source.movie_id = $source_id
        
        // Get source movie's properties for comparison
        OPTIONAL MATCH (source)-[:HAS_GENRE]->(source_genre:Genre)
        OPTIONAL MATCH (source)<-[:ACTED_IN]-(source_actor:Actor)
        OPTIONAL MATCH (source)<-[:DIRECTED]-(source_director:Director)
        
        WITH source, 
             collect(DISTINCT source_genre.name) as source_genres,
             collect(DISTINCT source_actor.name) as source_actors,
             collect(DISTINCT source_director.name) as source_directors,
             source.release_year as source_year
        
        // Find candidate movies through relationships
        MATCH (candidate:Movie)
        WHERE candidate.movie_id <> source.movie_id
        
        // Get candidate's relationships
        OPTIONAL MATCH (candidate)-[:HAS_GENRE]->(cand_genre:Genre)
        OPTIONAL MATCH (candidate)<-[:ACTED_IN]-(cand_actor:Actor)
        OPTIONAL MATCH (candidate)<-[:DIRECTED]-(cand_director:Director)
        
        WITH source, source_genres, source_actors, source_directors, source_year,
             candidate,
             collect(DISTINCT cand_genre.name) as cand_genres,
             collect(DISTINCT cand_actor.name) as cand_actors,
             collect(DISTINCT cand_director.name) as cand_directors
        
        // Calculate shared elements
        WITH source, candidate,
             source_genres, source_actors, source_directors, source_year,
             cand_genres, cand_actors, cand_directors,
             [g IN cand_genres WHERE g IN source_genres] as shared_genres,
             [a IN cand_actors WHERE a IN source_actors] as shared_actors,
             [d IN cand_directors WHERE d IN source_directors] as shared_directors,
             CASE 
                 WHEN candidate.release_year IS NOT NULL AND source_year IS NOT NULL
                 THEN abs(toInteger(candidate.release_year) - toInteger(source_year)) <= 10
                 ELSE false
             END as same_era
        
        // Calculate weighted similarity score
        WITH candidate,
             shared_genres, shared_actors, shared_directors, same_era,
             cand_genres, cand_actors, cand_directors,
             size(shared_genres) as genre_matches,
             size(shared_actors) as actor_matches,
             size(shared_directors) as director_matches,
             CASE WHEN same_era THEN 1 ELSE 0 END as era_match
        
        WITH candidate,
             shared_genres, shared_actors, shared_directors, same_era,
             cand_genres,
             genre_matches, actor_matches, director_matches, era_match,
             (genre_matches * $genre_weight) + 
             (actor_matches * $actor_weight) + 
             (director_matches * $director_weight) + 
             (era_match * $era_weight) as similarity_score
        
        // Filter to only movies with at least some similarity
        WHERE similarity_score > 0
        
        RETURN 
            candidate.movie_id as movie_id,
            candidate.title as title,
            candidate.overview as overview,
            candidate.release_year as release_year,
            candidate.vote_average as vote_average,
            candidate.poster_path as poster_path,
            candidate.popularity as popularity,
            cand_genres as genres,
            similarity_score,
            genre_matches,
            actor_matches,
            director_matches,
            era_match,
            shared_genres,
            shared_actors,
            shared_directors,
            same_era
        ORDER BY similarity_score DESC, candidate.vote_average DESC
        LIMIT $limit
        """
        
        try:
            with neo4j_service._driver.session() as session:
                # First get source movie ID
                result = session.run(source_query, params)
                source_record = result.single()
                
                if not source_record:
                    logger.warning(f"Source movie not found: {movie_id or movie_title}")
                    return [], {}
                
                source_movie = source_record["m"]
                source_id = source_movie["movie_id"]
                source_title = source_movie.get("title", "Unknown")
                
                # Run similarity query
                result = session.run(similarity_query, {
                    "source_id": source_id,
                    "limit": limit,
                    "genre_weight": genre_weight,
                    "actor_weight": actor_weight,
                    "director_weight": director_weight,
                    "era_weight": era_weight
                })
                
                movies = []
                for record in result:
                    movie = dict(record)
                    # Add match explanation
                    match_reasons = []
                    if movie["genre_matches"] > 0:
                        match_reasons.append(f"{movie['genre_matches']} shared genres: {', '.join(movie['shared_genres'][:3])}")
                    if movie["actor_matches"] > 0:
                        match_reasons.append(f"{movie['actor_matches']} shared actors: {', '.join(movie['shared_actors'][:2])}")
                    if movie["director_matches"] > 0:
                        match_reasons.append(f"same director: {', '.join(movie['shared_directors'])}")
                    if movie["same_era"]:
                        match_reasons.append(f"same era ({movie['release_year']}s)")
                    
                    movie["_match_reason"] = "; ".join(match_reasons)
                    movie["_similarity_score"] = movie["similarity_score"]
                    movies.append(movie)
                
                # Build similarity details for reasoning
                similarity_details = {
                    "source_movie": source_title,
                    "source_id": source_id,
                    "weights": {
                        "genre": genre_weight,
                        "actor": actor_weight,
                        "director": director_weight,
                        "era": era_weight
                    },
                    "total_found": len(movies)
                }
                
                logger.info(f"Found {len(movies)} similar movies to '{source_title}'")
                return movies, similarity_details
                
        except Exception as e:
            logger.error(f"Similar movies search error: {e}")
            return [], {}
    
    def find_movie_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Find a movie by its title (partial match).
        """
        query = """
        MATCH (m:Movie)
        WHERE m.title =~ $title_pattern
        OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
        OPTIONAL MATCH (d:Director)-[:DIRECTED]->(m)
        OPTIONAL MATCH (a:Actor)-[:ACTED_IN]->(m)
        WITH m, 
             collect(DISTINCT g.name) as genres,
             collect(DISTINCT d.name) as directors,
             collect(DISTINCT a.name)[0..5] as actors
        RETURN 
            m.movie_id as movie_id,
            m.title as title,
            m.overview as overview,
            m.release_year as release_year,
            m.vote_average as vote_average,
            m.poster_path as poster_path,
            genres,
            directors,
            actors
        ORDER BY m.popularity DESC
        LIMIT 1
        """
        
        try:
            with neo4j_service._driver.session() as session:
                result = session.run(query, {"title_pattern": f"(?i).*{title}.*"})
                record = result.single()
                if record:
                    return dict(record)
                return None
        except Exception as e:
            logger.error(f"Movie search error: {e}")
            return None


# Singleton instance
graph_query_service = GraphQueryService()

