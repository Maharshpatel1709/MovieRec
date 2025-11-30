"""
Model service for managing ML models.
"""
from typing import List, Dict, Any, Optional
import os
import pickle
from loguru import logger

from backend.config import settings
from backend.services.neo4j_service import neo4j_service


class ModelService:
    """Service for managing and running ML models."""
    
    def __init__(self):
        self._cbf_model = None
        self._cf_model = None
        self._hybrid_model = None
        self._kgnn_model = None
        self._models_loaded = False
    
    def load_models(self):
        """Load all ML models."""
        try:
            # Try to load pre-trained models
            models_dir = settings.models_dir
            
            # Content-Based Filtering
            cbf_path = os.path.join(models_dir, "cbf_model.pkl")
            if os.path.exists(cbf_path):
                with open(cbf_path, "rb") as f:
                    self._cbf_model = pickle.load(f)
                logger.info("CBF model loaded")
            else:
                logger.info("CBF model not found, using runtime computation")
            
            # Collaborative Filtering
            cf_path = os.path.join(models_dir, "cf_model.pkl")
            if os.path.exists(cf_path):
                with open(cf_path, "rb") as f:
                    self._cf_model = pickle.load(f)
                logger.info("CF model loaded")
            else:
                logger.info("CF model not found, using fallback")
            
            # KGNN
            kgnn_path = os.path.join(models_dir, "kgnn_model.pt")
            if os.path.exists(kgnn_path):
                from backend.models.kgnn import KGNNModel
                self._kgnn_model = KGNNModel.load(kgnn_path)
                logger.info("KGNN model loaded")
            else:
                logger.info("KGNN model not found, using fallback")
            
            self._models_loaded = True
            
        except Exception as e:
            logger.warning(f"Model loading error: {e}")
            self._models_loaded = False
    
    def get_hybrid_recommendations(
        self,
        user_id: Optional[int] = None,
        movie_ids: List[int] = None,
        genres: List[str] = None,
        n_recommendations: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get hybrid recommendations combining CBF and CF.
        """
        from backend.models.hybrid import HybridRecommender
        
        recommender = HybridRecommender()
        
        try:
            recommendations = recommender.recommend(
                user_id=user_id,
                movie_ids=movie_ids or [],
                genres=genres or [],
                n_recommendations=n_recommendations
            )
            
            return [
                {
                    "movie_id": rec["movie_id"],
                    "title": rec["title"],
                    "score": rec["score"],
                    "genres": rec.get("genres", []),
                    "poster_path": rec.get("poster_path"),
                    "overview": rec.get("overview"),
                    "release_year": rec.get("release_year"),
                    "explanation": rec.get("explanation", "Recommended based on your preferences")
                }
                for rec in recommendations
            ]
        except Exception as e:
            logger.error(f"Hybrid recommendation error: {e}")
            return self._get_fallback_recommendations(n_recommendations, genres)
    
    def get_kgnn_recommendations(
        self,
        user_id: Optional[int] = None,
        movie_ids: List[int] = None,
        n_recommendations: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations using KGNN.
        """
        from backend.models.kgnn import KGNNRecommender
        
        try:
            recommender = KGNNRecommender()
            
            recommendations = recommender.recommend(
                user_id=user_id,
                movie_ids=movie_ids or [],
                n_recommendations=n_recommendations
            )
            
            return [
                {
                    "movie_id": rec["movie_id"],
                    "title": rec["title"],
                    "score": rec["score"],
                    "genres": rec.get("genres", []),
                    "poster_path": rec.get("poster_path"),
                    "overview": rec.get("overview"),
                    "release_year": rec.get("release_year"),
                    "explanation": "Recommended using graph neural network analysis"
                }
                for rec in recommendations
            ]
        except Exception as e:
            logger.error(f"KGNN recommendation error: {e}")
            return self._get_fallback_recommendations(n_recommendations)
    
    def get_similar_movies(
        self,
        movie_id: int,
        n_recommendations: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get similar movies using content-based filtering.
        """
        from backend.models.cbf import ContentBasedFilter
        
        try:
            cbf = ContentBasedFilter()
            recommendations = cbf.get_similar(
                movie_id=movie_id,
                n_recommendations=n_recommendations
            )
            
            return [
                {
                    "movie_id": rec["movie_id"],
                    "title": rec["title"],
                    "score": rec["score"],
                    "genres": rec.get("genres", []),
                    "poster_path": rec.get("poster_path"),
                    "overview": rec.get("overview"),
                    "release_year": rec.get("release_year"),
                    "explanation": f"Similar to the movie you selected"
                }
                for rec in recommendations
            ]
        except Exception as e:
            logger.error(f"Similar movies error: {e}")
            return self._get_fallback_recommendations(n_recommendations)
    
    def get_popular_movies(
        self,
        n_recommendations: int = 10,
        genre: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get popular movies, optionally filtered by genre.
        """
        try:
            genres = [genre] if genre else None
            results = neo4j_service.search_movies(
                genres=genres,
                limit=n_recommendations
            )
            
            return [
                {
                    "movie_id": r["movie_id"],
                    "title": r["title"],
                    "score": r.get("popularity", 1.0),
                    "genres": r.get("genres", []),
                    "poster_path": r.get("poster_path"),
                    "overview": r.get("overview"),
                    "release_year": r.get("release_year"),
                    "explanation": "Popular movie" + (f" in {genre}" if genre else "")
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Popular movies error: {e}")
            return []
    
    def _get_fallback_recommendations(
        self,
        n_recommendations: int,
        genres: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get fallback recommendations when models fail."""
        try:
            results = neo4j_service.search_movies(
                genres=genres,
                limit=n_recommendations
            )
            
            return [
                {
                    "movie_id": r["movie_id"],
                    "title": r["title"],
                    "score": 0.5,
                    "genres": r.get("genres", []),
                    "poster_path": r.get("poster_path"),
                    "overview": r.get("overview"),
                    "release_year": r.get("release_year"),
                    "explanation": "Popular recommendation"
                }
                for r in results
            ]
        except Exception:
            return []


# Singleton instance
model_service = ModelService()

