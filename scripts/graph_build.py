"""
Neo4j Graph Building Script
Creates the movie knowledge graph in Neo4j.
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
from neo4j import GraphDatabase
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings


# Configuration
PROCESSED_DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
BATCH_SIZE = 1000


class GraphBuilder:
    """Build the movie knowledge graph in Neo4j."""
    
    def __init__(self):
        self._driver = None
    
    def connect(self):
        """Connect to Neo4j database."""
        try:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            self._driver.verify_connectivity()
            logger.info("Connected to Neo4j")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
    
    def run_query(self, query: str, params: Dict = None):
        """Execute a Cypher query."""
        with self._driver.session() as session:
            return session.run(query, params or {})
    
    def clear_database(self):
        """Clear all data from the database."""
        logger.info("Clearing existing data...")
        self.run_query("MATCH (n) DETACH DELETE n")
        logger.info("Database cleared")
    
    def create_constraints(self):
        """Create uniqueness constraints and indexes."""
        logger.info("Creating constraints and indexes...")
        
        constraints = [
            "CREATE CONSTRAINT movie_id IF NOT EXISTS FOR (m:Movie) REQUIRE m.movie_id IS UNIQUE",
            "CREATE CONSTRAINT actor_id IF NOT EXISTS FOR (a:Actor) REQUIRE a.actor_id IS UNIQUE",
            "CREATE CONSTRAINT director_id IF NOT EXISTS FOR (d:Director) REQUIRE d.director_id IS UNIQUE",
            "CREATE CONSTRAINT genre_name IF NOT EXISTS FOR (g:Genre) REQUIRE g.name IS UNIQUE",
        ]
        
        indexes = [
            "CREATE INDEX movie_title IF NOT EXISTS FOR (m:Movie) ON (m.title)",
            "CREATE INDEX movie_year IF NOT EXISTS FOR (m:Movie) ON (m.release_year)",
            "CREATE INDEX movie_popularity IF NOT EXISTS FOR (m:Movie) ON (m.popularity)",
        ]
        
        for query in constraints + indexes:
            try:
                self.run_query(query)
            except Exception as e:
                logger.warning(f"Constraint/Index creation warning: {e}")
        
        logger.info("Constraints and indexes created")
    
    def load_genres(self, genres_df: pd.DataFrame):
        """Load genre nodes."""
        logger.info("Loading genres...")
        
        query = """
        UNWIND $genres as genre
        MERGE (g:Genre {name: genre.name})
        SET g.genre_id = genre.genre_id
        """
        
        genres = genres_df.to_dict('records')
        self.run_query(query, {'genres': genres})
        
        logger.info(f"Loaded {len(genres)} genres")
    
    def load_movies(self, movies_df: pd.DataFrame):
        """Load movie nodes in batches."""
        logger.info("Loading movies...")
        
        query = """
        UNWIND $movies as movie
        MERGE (m:Movie {movie_id: movie.movie_id})
        SET m.title = movie.title,
            m.original_title = movie.original_title,
            m.overview = movie.overview,
            m.tagline = movie.tagline,
            m.release_date = movie.release_date,
            m.release_year = movie.release_year,
            m.runtime = movie.runtime,
            m.budget = movie.budget,
            m.revenue = movie.revenue,
            m.popularity = movie.popularity,
            m.vote_average = movie.vote_average,
            m.vote_count = movie.vote_count,
            m.poster_path = movie.poster_path,
            m.backdrop_path = movie.backdrop_path,
            m.original_language = movie.original_language,
            m.imdb_id = movie.imdb_id
        """
        
        # Convert DataFrame to records, handling NaN values
        movies = movies_df.fillna('').to_dict('records')
        
        # Process in batches
        for i in range(0, len(movies), BATCH_SIZE):
            batch = movies[i:i + BATCH_SIZE]
            self.run_query(query, {'movies': batch})
            logger.info(f"Loaded movies batch {i // BATCH_SIZE + 1}")
        
        logger.info(f"Loaded {len(movies)} movies")
    
    def load_actors(self, actors_df: pd.DataFrame):
        """Load actor nodes."""
        logger.info("Loading actors...")
        
        query = """
        UNWIND $actors as actor
        MERGE (a:Actor {actor_id: actor.actor_id})
        SET a.name = actor.name,
            a.gender = actor.gender,
            a.profile_path = actor.profile_path
        """
        
        actors = actors_df.fillna('').to_dict('records')
        
        for i in range(0, len(actors), BATCH_SIZE):
            batch = actors[i:i + BATCH_SIZE]
            self.run_query(query, {'actors': batch})
        
        logger.info(f"Loaded {len(actors)} actors")
    
    def load_directors(self, directors_df: pd.DataFrame):
        """Load director nodes."""
        logger.info("Loading directors...")
        
        query = """
        UNWIND $directors as director
        MERGE (d:Director {director_id: director.director_id})
        SET d.name = director.name,
            d.gender = director.gender,
            d.profile_path = director.profile_path
        """
        
        directors = directors_df.fillna('').to_dict('records')
        
        for i in range(0, len(directors), BATCH_SIZE):
            batch = directors[i:i + BATCH_SIZE]
            self.run_query(query, {'directors': batch})
        
        logger.info(f"Loaded {len(directors)} directors")
    
    def create_movie_genre_relationships(self, movie_genres_df: pd.DataFrame):
        """Create HAS_GENRE relationships."""
        logger.info("Creating movie-genre relationships...")
        
        query = """
        UNWIND $relationships as rel
        MATCH (m:Movie {movie_id: rel.movie_id})
        MATCH (g:Genre {name: rel.genre_name})
        MERGE (m)-[:HAS_GENRE]->(g)
        """
        
        relationships = movie_genres_df.to_dict('records')
        
        for i in range(0, len(relationships), BATCH_SIZE):
            batch = relationships[i:i + BATCH_SIZE]
            self.run_query(query, {'relationships': batch})
        
        logger.info(f"Created {len(relationships)} movie-genre relationships")
    
    def create_actor_relationships(self, movie_actors_df: pd.DataFrame):
        """Create ACTED_IN relationships."""
        logger.info("Creating actor-movie relationships...")
        
        query = """
        UNWIND $relationships as rel
        MATCH (a:Actor {actor_id: rel.actor_id})
        MATCH (m:Movie {movie_id: rel.movie_id})
        MERGE (a)-[r:ACTED_IN]->(m)
        SET r.character = rel.character,
            r.order = rel.order
        """
        
        relationships = movie_actors_df.fillna('').to_dict('records')
        
        for i in range(0, len(relationships), BATCH_SIZE):
            batch = relationships[i:i + BATCH_SIZE]
            self.run_query(query, {'relationships': batch})
        
        logger.info(f"Created {len(relationships)} actor-movie relationships")
    
    def create_director_relationships(self, movie_directors_df: pd.DataFrame):
        """Create DIRECTED relationships."""
        logger.info("Creating director-movie relationships...")
        
        query = """
        UNWIND $relationships as rel
        MATCH (d:Director {director_id: rel.director_id})
        MATCH (m:Movie {movie_id: rel.movie_id})
        MERGE (d)-[:DIRECTED]->(m)
        """
        
        relationships = movie_directors_df.to_dict('records')
        
        for i in range(0, len(relationships), BATCH_SIZE):
            batch = relationships[i:i + BATCH_SIZE]
            self.run_query(query, {'relationships': batch})
        
        logger.info(f"Created {len(relationships)} director-movie relationships")
    
    def create_vector_index(self):
        """Create vector index for movie embeddings."""
        logger.info("Creating vector index...")
        
        try:
            # Drop existing index if exists
            self.run_query("DROP INDEX movie_embeddings IF EXISTS")
        except:
            pass
        
        # Create vector index
        query = """
        CREATE VECTOR INDEX movie_embeddings IF NOT EXISTS
        FOR (m:Movie)
        ON m.embedding
        OPTIONS {
            indexConfig: {
                `vector.dimensions`: 768,
                `vector.similarity_function`: 'cosine'
            }
        }
        """
        
        try:
            self.run_query(query)
            logger.info("Vector index created")
        except Exception as e:
            logger.warning(f"Vector index creation failed (may require Neo4j 5.11+): {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        stats = {}
        
        queries = {
            'movies': "MATCH (m:Movie) RETURN count(m) as count",
            'actors': "MATCH (a:Actor) RETURN count(a) as count",
            'directors': "MATCH (d:Director) RETURN count(d) as count",
            'genres': "MATCH (g:Genre) RETURN count(g) as count",
            'acted_in': "MATCH ()-[r:ACTED_IN]->() RETURN count(r) as count",
            'directed': "MATCH ()-[r:DIRECTED]->() RETURN count(r) as count",
            'has_genre': "MATCH ()-[r:HAS_GENRE]->() RETURN count(r) as count",
        }
        
        with self._driver.session() as session:
            for name, query in queries.items():
                result = session.run(query)
                record = result.single()
                stats[name] = record['count'] if record else 0
        
        return stats


def load_data_files() -> Dict[str, pd.DataFrame]:
    """Load processed data files."""
    files = {
        'movies': 'movies.csv',
        'genres': 'genres.csv',
        'movie_genres': 'movie_genres.csv',
        'actors': 'actors.csv',
        'directors': 'directors.csv',
        'movie_actors': 'movie_actors.csv',
        'movie_directors': 'movie_directors.csv',
    }
    
    data = {}
    for name, filename in files.items():
        filepath = PROCESSED_DATA_DIR / filename
        if filepath.exists():
            data[name] = pd.read_csv(filepath)
            logger.info(f"Loaded {filename}: {len(data[name])} records")
        else:
            logger.warning(f"File not found: {filename}")
    
    return data


def main():
    """Main graph building pipeline."""
    logger.info("Starting graph building...")
    
    # Load data
    data = load_data_files()
    
    if 'movies' not in data:
        logger.error("Movies data not found. Run preprocessing first.")
        return
    
    # Build graph
    builder = GraphBuilder()
    
    try:
        builder.connect()
        
        # Clear and setup
        builder.clear_database()
        builder.create_constraints()
        
        # Load nodes
        if 'genres' in data:
            builder.load_genres(data['genres'])
        
        builder.load_movies(data['movies'])
        
        if 'actors' in data:
            builder.load_actors(data['actors'])
        
        if 'directors' in data:
            builder.load_directors(data['directors'])
        
        # Create relationships
        if 'movie_genres' in data:
            builder.create_movie_genre_relationships(data['movie_genres'])
        
        if 'movie_actors' in data:
            builder.create_actor_relationships(data['movie_actors'])
        
        if 'movie_directors' in data:
            builder.create_director_relationships(data['movie_directors'])
        
        # Create vector index
        builder.create_vector_index()
        
        # Print stats
        stats = builder.get_stats()
        logger.info("\n=== Graph Statistics ===")
        for name, count in stats.items():
            logger.info(f"{name}: {count}")
        
        logger.info("Graph building complete!")
        
    except Exception as e:
        logger.error(f"Graph building failed: {e}")
        raise
    finally:
        builder.close()


if __name__ == "__main__":
    main()

