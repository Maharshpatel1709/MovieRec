"""
Collaborative Filtering (CF) Model.
Uses SVD and KNN for user-item recommendations.
"""
import os
import pickle
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from sklearn.neighbors import NearestNeighbors
from loguru import logger
import pandas as pd

from backend.config import settings


class CollaborativeFilter:
    """Collaborative filtering using SVD and KNN."""
    
    def __init__(self):
        self._user_item_matrix = None
        self._svd_model = None
        self._knn_model = None
        self._user_ids = []
        self._movie_ids = []
        self._user_to_idx = {}
        self._movie_to_idx = {}
        self._idx_to_movie = {}
        self._predicted_ratings = None
        self._loaded = False
    
    def _load_or_compute(self):
        """Load pre-computed model or compute from scratch."""
        if self._loaded:
            return
        
        model_path = os.path.join(settings.models_dir, "cf_model.pkl")
        
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    data = pickle.load(f)
                    self._user_item_matrix = data["matrix"]
                    self._user_ids = data["user_ids"]
                    self._movie_ids = data["movie_ids"]
                    self._user_to_idx = data["user_to_idx"]
                    self._movie_to_idx = data["movie_to_idx"]
                    self._idx_to_movie = data["idx_to_movie"]
                    self._predicted_ratings = data.get("predicted_ratings")
                self._loaded = True
                logger.info("CF model loaded from disk")
                return
            except Exception as e:
                logger.warning(f"Failed to load CF model: {e}")
        
        # Load from ratings data if available
        self._load_from_data()
    
    def _load_from_data(self):
        """Load and compute CF model from ratings data."""
        ratings_path = os.path.join(settings.processed_data_dir, "ratings.csv")
        
        if not os.path.exists(ratings_path):
            logger.warning("Ratings data not found, creating minimal model")
            self._create_minimal_model()
            return
        
        try:
            # Load ratings
            ratings_df = pd.read_csv(ratings_path)
            
            # Create user-item matrix
            self._user_ids = ratings_df["userId"].unique().tolist()
            self._movie_ids = ratings_df["movieId"].unique().tolist()
            
            self._user_to_idx = {uid: i for i, uid in enumerate(self._user_ids)}
            self._movie_to_idx = {mid: i for i, mid in enumerate(self._movie_ids)}
            self._idx_to_movie = {i: mid for mid, i in self._movie_to_idx.items()}
            
            # Build sparse matrix
            rows = [self._user_to_idx[uid] for uid in ratings_df["userId"]]
            cols = [self._movie_to_idx[mid] for mid in ratings_df["movieId"]]
            data = ratings_df["rating"].values
            
            self._user_item_matrix = csr_matrix(
                (data, (rows, cols)),
                shape=(len(self._user_ids), len(self._movie_ids))
            )
            
            # Compute SVD
            self._compute_svd()
            
            self._loaded = True
            logger.info(f"CF model computed: {len(self._user_ids)} users, {len(self._movie_ids)} movies")
            
        except Exception as e:
            logger.error(f"Failed to load ratings data: {e}")
            self._create_minimal_model()
    
    def _compute_svd(self, n_factors: int = 50):
        """Compute SVD factorization."""
        if self._user_item_matrix is None:
            return
        
        try:
            # Normalize matrix
            matrix = self._user_item_matrix.toarray()
            user_ratings_mean = np.mean(matrix, axis=1).reshape(-1, 1)
            matrix_normalized = matrix - user_ratings_mean
            
            # SVD
            n_factors = min(n_factors, min(matrix.shape) - 1)
            U, sigma, Vt = svds(csr_matrix(matrix_normalized), k=n_factors)
            
            # Reconstruct predictions
            sigma_diag = np.diag(sigma)
            self._predicted_ratings = np.dot(np.dot(U, sigma_diag), Vt) + user_ratings_mean
            
            logger.info(f"SVD computed with {n_factors} factors")
            
        except Exception as e:
            logger.warning(f"SVD computation failed: {e}")
            self._predicted_ratings = None
    
    def _create_minimal_model(self):
        """Create a minimal model when no data is available."""
        self._user_ids = []
        self._movie_ids = []
        self._user_to_idx = {}
        self._movie_to_idx = {}
        self._idx_to_movie = {}
        self._user_item_matrix = None
        self._predicted_ratings = None
        self._loaded = True
    
    def get_recommendations_for_user(
        self,
        user_id: int,
        n_recommendations: int = 10,
        exclude_rated: bool = True
    ) -> List[Tuple[int, float]]:
        """
        Get movie recommendations for a user.
        Returns list of (movie_id, predicted_rating) tuples.
        """
        self._load_or_compute()
        
        if user_id not in self._user_to_idx or self._predicted_ratings is None:
            return []
        
        user_idx = self._user_to_idx[user_id]
        predictions = self._predicted_ratings[user_idx]
        
        if exclude_rated and self._user_item_matrix is not None:
            # Mask already rated movies
            rated_mask = self._user_item_matrix[user_idx].toarray().flatten() > 0
            predictions = np.where(rated_mask, -np.inf, predictions)
        
        # Get top predictions
        top_indices = predictions.argsort()[::-1][:n_recommendations]
        
        return [
            (self._idx_to_movie[idx], float(predictions[idx]))
            for idx in top_indices
            if idx in self._idx_to_movie
        ]
    
    def get_similar_users(
        self,
        user_id: int,
        n_neighbors: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Find similar users using KNN.
        Returns list of (user_id, similarity) tuples.
        """
        self._load_or_compute()
        
        if user_id not in self._user_to_idx or self._user_item_matrix is None:
            return []
        
        # Fit KNN if not already done
        if self._knn_model is None:
            self._knn_model = NearestNeighbors(
                metric="cosine",
                algorithm="brute",
                n_neighbors=min(n_neighbors + 1, len(self._user_ids))
            )
            self._knn_model.fit(self._user_item_matrix)
        
        user_idx = self._user_to_idx[user_id]
        user_vector = self._user_item_matrix[user_idx]
        
        distances, indices = self._knn_model.kneighbors(
            user_vector,
            n_neighbors=n_neighbors + 1
        )
        
        # Convert to user IDs (excluding the user itself)
        similar_users = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != user_idx and idx < len(self._user_ids):
                similar_users.append((self._user_ids[idx], 1 - dist))  # Convert distance to similarity
        
        return similar_users[:n_neighbors]
    
    def get_similar_movies(
        self,
        movie_id: int,
        n_neighbors: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Find similar movies based on user rating patterns.
        Returns list of (movie_id, similarity) tuples.
        """
        self._load_or_compute()
        
        if movie_id not in self._movie_to_idx or self._user_item_matrix is None:
            return []
        
        # Use item-item similarity (transpose of user-item matrix)
        item_matrix = self._user_item_matrix.T
        
        movie_idx = self._movie_to_idx[movie_id]
        movie_vector = item_matrix[movie_idx]
        
        # Compute cosine similarities
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(movie_vector, item_matrix).flatten()
        
        # Get top similar (excluding itself)
        top_indices = similarities.argsort()[::-1]
        
        similar_movies = []
        for idx in top_indices:
            if idx != movie_idx and idx in self._idx_to_movie:
                similar_movies.append((self._idx_to_movie[idx], float(similarities[idx])))
                if len(similar_movies) >= n_neighbors:
                    break
        
        return similar_movies
    
    def predict_rating(self, user_id: int, movie_id: int) -> Optional[float]:
        """Predict rating for a user-movie pair."""
        self._load_or_compute()
        
        if (user_id not in self._user_to_idx or 
            movie_id not in self._movie_to_idx or 
            self._predicted_ratings is None):
            return None
        
        user_idx = self._user_to_idx[user_id]
        movie_idx = self._movie_to_idx[movie_id]
        
        return float(self._predicted_ratings[user_idx, movie_idx])
    
    def save_model(self, path: Optional[str] = None):
        """Save the model to disk."""
        if not self._loaded:
            self._load_or_compute()
        
        path = path or os.path.join(settings.models_dir, "cf_model.pkl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "wb") as f:
            pickle.dump({
                "matrix": self._user_item_matrix,
                "user_ids": self._user_ids,
                "movie_ids": self._movie_ids,
                "user_to_idx": self._user_to_idx,
                "movie_to_idx": self._movie_to_idx,
                "idx_to_movie": self._idx_to_movie,
                "predicted_ratings": self._predicted_ratings
            }, f)
        
        logger.info(f"CF model saved to {path}")

