"""
Embedding Generation Script
Generates embeddings for movie overviews and stores them in Neo4j.
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

import pandas as pd
import numpy as np
from neo4j import GraphDatabase
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.services.embedding_service import EmbeddingService


# Configuration
PROCESSED_DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
EMBEDDINGS_DIR = Path(__file__).parent.parent / "data" / "embeddings"
BATCH_SIZE = 100


class EmbeddingGenerator:
    """Generate and store movie embeddings."""
    
    def __init__(self):
        self._driver = None
        self._embedding_service = EmbeddingService()
    
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
        """Execute a Cypher query (for write operations)."""
        with self._driver.session() as session:
            session.run(query, params or {})
    
    def get_movies_without_embeddings(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get movies that don't have embeddings yet."""
        query = """
        MATCH (m:Movie)
        WHERE m.embedding IS NULL AND m.overview IS NOT NULL AND m.overview <> ''
        RETURN m.movie_id as movie_id, m.title as title, m.overview as overview
        """
        if limit:
            query += f" LIMIT {limit}"
        
        with self._driver.session() as session:
            result = session.run(query)
            return [dict(record) for record in result]
    
    def get_all_movies_for_embedding(self) -> List[Dict[str, Any]]:
        """Get all movies for embedding generation."""
        query = """
        MATCH (m:Movie)
        WHERE m.overview IS NOT NULL AND m.overview <> ''
        RETURN m.movie_id as movie_id, m.title as title, m.overview as overview,
               [(m)-[:HAS_GENRE]->(g:Genre) | g.name] as genres
        """
        
        with self._driver.session() as session:
            result = session.run(query)
            return [dict(record) for record in result]
    
    def create_embedding_text(self, movie: Dict[str, Any]) -> str:
        """Create rich text for embedding from movie data."""
        parts = []
        
        if movie.get('title'):
            parts.append(f"Title: {movie['title']}")
        
        if movie.get('genres'):
            genres = movie['genres'] if isinstance(movie['genres'], list) else []
            if genres:
                parts.append(f"Genres: {', '.join(genres)}")
        
        if movie.get('overview'):
            parts.append(f"Overview: {movie['overview']}")
        
        return " ".join(parts)
    
    def store_embedding(self, movie_id: int, embedding: List[float]):
        """Store embedding for a movie in Neo4j."""
        query = """
        MATCH (m:Movie {movie_id: $movie_id})
        SET m.embedding = $embedding
        """
        self.run_query(query, {'movie_id': movie_id, 'embedding': embedding})
    
    def store_embeddings_batch(self, embeddings: List[Dict[str, Any]]):
        """Store multiple embeddings in batch."""
        query = """
        UNWIND $embeddings as item
        MATCH (m:Movie {movie_id: item.movie_id})
        SET m.embedding = item.embedding
        """
        self.run_query(query, {'embeddings': embeddings})
    
    def generate_and_store_embeddings(self, movies: List[Dict[str, Any]]):
        """Generate embeddings for movies and store in Neo4j."""
        logger.info(f"Generating embeddings for {len(movies)} movies...")
        
        # Process in batches
        for i in range(0, len(movies), BATCH_SIZE):
            batch = movies[i:i + BATCH_SIZE]
            
            # Create texts for embedding
            texts = [self.create_embedding_text(m) for m in batch]
            
            # Generate embeddings
            embeddings = self._embedding_service.generate_embeddings_batch(texts)
            
            # Prepare for storage
            embedding_records = [
                {'movie_id': movie['movie_id'], 'embedding': emb}
                for movie, emb in zip(batch, embeddings)
            ]
            
            # Store in Neo4j
            self.store_embeddings_batch(embedding_records)
            
            logger.info(f"Processed batch {i // BATCH_SIZE + 1}/{(len(movies) + BATCH_SIZE - 1) // BATCH_SIZE}")
        
        logger.info("Embedding generation complete")
    
    def create_vector_index(self):
        """Create or recreate vector index for embeddings."""
        logger.info("Creating vector index...")
        
        # Drop existing index
        try:
            self.run_query("DROP INDEX movie_embeddings IF EXISTS")
        except:
            pass
        
        # Get embedding dimension
        dimension = self._embedding_service.dimension
        
        # Create vector index
        query = f"""
        CREATE VECTOR INDEX movie_embeddings IF NOT EXISTS
        FOR (m:Movie)
        ON m.embedding
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {dimension},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """
        
        try:
            self.run_query(query)
            logger.info(f"Vector index created with dimension {dimension}")
        except Exception as e:
            logger.warning(f"Vector index creation failed: {e}")
            logger.info("Note: Vector indexes require Neo4j 5.11+ with vector index support")
    
    def save_embeddings_to_file(self, movies: List[Dict[str, Any]], embeddings: List[List[float]]):
        """Save embeddings to file for backup."""
        os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
        
        # Save as numpy array
        movie_ids = [m['movie_id'] for m in movies]
        embeddings_array = np.array(embeddings)
        
        np.save(EMBEDDINGS_DIR / 'movie_embeddings.npy', embeddings_array)
        
        # Save movie ID mapping
        with open(EMBEDDINGS_DIR / 'movie_ids.json', 'w') as f:
            json.dump(movie_ids, f)
        
        logger.info(f"Embeddings saved to {EMBEDDINGS_DIR}")
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get statistics about stored embeddings."""
        query = """
        MATCH (m:Movie)
        WITH count(m) as total_movies,
             sum(CASE WHEN m.embedding IS NOT NULL THEN 1 ELSE 0 END) as with_embeddings
        RETURN total_movies, with_embeddings,
               round(100.0 * with_embeddings / total_movies, 2) as coverage_percent
        """
        
        with self._driver.session() as session:
            result = session.run(query)
            record = result.single()
            return dict(record) if record else {}


def main():
    """Main embedding generation pipeline."""
    logger.info("Starting embedding generation...")
    
    generator = EmbeddingGenerator()
    
    try:
        generator.connect()
        
        # Get movies
        movies = generator.get_all_movies_for_embedding()
        
        if not movies:
            logger.warning("No movies found for embedding generation")
            return
        
        logger.info(f"Found {len(movies)} movies for embedding")
        
        # Generate and store embeddings
        generator.generate_and_store_embeddings(movies)
        
        # Create vector index
        generator.create_vector_index()
        
        # Print stats
        stats = generator.get_embedding_stats()
        logger.info("\n=== Embedding Statistics ===")
        logger.info(f"Total movies: {stats.get('total_movies', 0)}")
        logger.info(f"With embeddings: {stats.get('with_embeddings', 0)}")
        logger.info(f"Coverage: {stats.get('coverage_percent', 0)}%")
        
        logger.info("Embedding generation complete!")
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise
    finally:
        generator.close()


if __name__ == "__main__":
    main()

