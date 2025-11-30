"""
Content-Based Filtering (CBF) Model.
Uses TF-IDF and cosine similarity for movie recommendations.
"""
import os
import pickle
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from loguru import logger
import pandas as pd

from backend.config import settings
from backend.services.neo4j_service import neo4j_service


class ContentBasedFilter:
    """Content-based filtering using TF-IDF on movie metadata."""
    
    def __init__(self):
        self._tfidf_vectorizer = None
        self._tfidf_matrix = None
        self._movie_indices = {}  # movie_id -> index mapping
        self._movies_data = None
        self._loaded = False
    
    def _load_or_compute(self):
        """Load pre-computed model or compute from scratch."""
        if self._loaded:
            return
        
        model_path = os.path.join(settings.models_dir, "cbf_model.pkl")
        
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    data = pickle.load(f)
                    self._tfidf_vectorizer = data["vectorizer"]
                    self._tfidf_matrix = data["matrix"]
                    self._movie_indices = data["indices"]
                    self._movies_data = data["movies"]
                self._loaded = True
                logger.info("CBF model loaded from disk")
                return
            except Exception as e:
                logger.warning(f"Failed to load CBF model: {e}")
        
        # Compute from Neo4j data
        self._compute_from_database()
    
    def _compute_from_database(self):
        """Compute TF-IDF matrix from database."""
        try:
            # Get movies from Neo4j
            movies = neo4j_service.search_movies(limit=10000)
            
            if not movies:
                logger.warning("No movies found in database, using fallback")
                self._create_fallback_model()
                return
            
            self._movies_data = movies
            
            # Create content strings for TF-IDF
            contents = []
            for i, movie in enumerate(movies):
                self._movie_indices[movie["movie_id"]] = i
                
                # Combine metadata for content
                content_parts = []
                
                if movie.get("title"):
                    content_parts.append(movie["title"])
                
                if movie.get("overview"):
                    content_parts.append(movie["overview"])
                
                if movie.get("genres"):
                    content_parts.extend(movie["genres"] * 2)  # Weight genres
                
                contents.append(" ".join(content_parts))
            
            # Create TF-IDF matrix
            self._tfidf_vectorizer = TfidfVectorizer(
                stop_words="english",
                max_features=5000,
                ngram_range=(1, 2)
            )
            self._tfidf_matrix = self._tfidf_vectorizer.fit_transform(contents)
            self._loaded = True
            
            logger.info(f"CBF model computed for {len(movies)} movies")
            
        except Exception as e:
            logger.error(f"Failed to compute CBF model: {e}")
            self._create_fallback_model()
    
    def _create_fallback_model(self):
        """Create a minimal fallback model."""
        self._movies_data = []
        self._tfidf_vectorizer = TfidfVectorizer()
        self._tfidf_matrix = None
        self._loaded = True
    
    def get_similar(
        self,
        movie_id: int,
        n_recommendations: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get movies similar to the given movie.
        """
        self._load_or_compute()
        
        if self._tfidf_matrix is None or movie_id not in self._movie_indices:
            # Fallback to database search
            movie = neo4j_service.get_movie_details(movie_id)
            if movie and movie.get("genres"):
                return neo4j_service.search_movies(
                    genres=movie["genres"][:2],
                    limit=n_recommendations
                )
            return []
        
        # Get index for the movie
        idx = self._movie_indices[movie_id]
        
        # Compute cosine similarity
        movie_vector = self._tfidf_matrix[idx]
        similarities = cosine_similarity(movie_vector, self._tfidf_matrix).flatten()
        
        # Get top similar movies (excluding itself)
        similar_indices = similarities.argsort()[::-1][1:n_recommendations + 1]
        
        results = []
        for i in similar_indices:
            movie = self._movies_data[i]
            results.append({
                "movie_id": movie["movie_id"],
                "title": movie["title"],
                "score": float(similarities[i]),
                "genres": movie.get("genres", []),
                "overview": movie.get("overview"),
                "release_year": movie.get("release_year"),
                "poster_path": movie.get("poster_path")
            })
        
        return results
    
    def get_recommendations_for_text(
        self,
        text: str,
        n_recommendations: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get movie recommendations based on text description.
        """
        self._load_or_compute()
        
        if self._tfidf_matrix is None:
            return []
        
        # Transform text to TF-IDF vector
        text_vector = self._tfidf_vectorizer.transform([text])
        
        # Compute similarities
        similarities = cosine_similarity(text_vector, self._tfidf_matrix).flatten()
        
        # Get top movies
        top_indices = similarities.argsort()[::-1][:n_recommendations]
        
        results = []
        for i in top_indices:
            movie = self._movies_data[i]
            results.append({
                "movie_id": movie["movie_id"],
                "title": movie["title"],
                "score": float(similarities[i]),
                "genres": movie.get("genres", []),
                "overview": movie.get("overview"),
                "release_year": movie.get("release_year"),
                "poster_path": movie.get("poster_path")
            })
        
        return results
    
    def save_model(self, path: Optional[str] = None):
        """Save the model to disk."""
        if not self._loaded:
            self._load_or_compute()
        
        path = path or os.path.join(settings.models_dir, "cbf_model.pkl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "wb") as f:
            pickle.dump({
                "vectorizer": self._tfidf_vectorizer,
                "matrix": self._tfidf_matrix,
                "indices": self._movie_indices,
                "movies": self._movies_data
            }, f)
        
        logger.info(f"CBF model saved to {path}")

