"""
Hybrid Recommender combining Content-Based and Collaborative Filtering.
"""
from typing import List, Dict, Any, Optional
import numpy as np
from loguru import logger

from backend.models.cbf import ContentBasedFilter
from backend.models.cf import CollaborativeFilter
from backend.services.neo4j_service import neo4j_service
from backend.services.embedding_service import embedding_service


class HybridRecommender:
    """
    Hybrid recommender that combines multiple recommendation strategies:
    - Content-Based Filtering (CBF)
    - Collaborative Filtering (CF)
    - Semantic similarity using embeddings
    """
    
    def __init__(
        self,
        cbf_weight: float = 0.4,
        cf_weight: float = 0.3,
        semantic_weight: float = 0.3
    ):
        """
        Initialize hybrid recommender with strategy weights.
        
        Args:
            cbf_weight: Weight for content-based filtering
            cf_weight: Weight for collaborative filtering
            semantic_weight: Weight for semantic similarity
        """
        self._cbf = ContentBasedFilter()
        self._cf = CollaborativeFilter()
        self._cbf_weight = cbf_weight
        self._cf_weight = cf_weight
        self._semantic_weight = semantic_weight
    
    def recommend(
        self,
        user_id: Optional[int] = None,
        movie_ids: List[int] = None,
        genres: List[str] = None,
        text_query: Optional[str] = None,
        n_recommendations: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get hybrid recommendations.
        
        Args:
            user_id: Optional user ID for personalized recommendations
            movie_ids: Optional list of movie IDs user has liked
            genres: Optional list of preferred genres
            text_query: Optional text description of desired movies
            n_recommendations: Number of recommendations to return
        """
        movie_ids = movie_ids or []
        genres = genres or []
        
        # Collect recommendations from each strategy
        all_recommendations = {}
        
        # 1. Content-Based Filtering
        cbf_recs = self._get_cbf_recommendations(movie_ids, text_query, n_recommendations * 2)
        for rec in cbf_recs:
            mid = rec["movie_id"]
            if mid not in all_recommendations:
                all_recommendations[mid] = {
                    "movie_id": mid,
                    "scores": {"cbf": 0, "cf": 0, "semantic": 0},
                    "data": rec
                }
            all_recommendations[mid]["scores"]["cbf"] = rec["score"]
        
        # 2. Collaborative Filtering (if user_id provided)
        if user_id:
            cf_recs = self._get_cf_recommendations(user_id, n_recommendations * 2)
            for mid, score in cf_recs:
                if mid not in all_recommendations:
                    movie_data = neo4j_service.get_movie_details(mid)
                    if movie_data:
                        all_recommendations[mid] = {
                            "movie_id": mid,
                            "scores": {"cbf": 0, "cf": 0, "semantic": 0},
                            "data": {
                                "movie_id": mid,
                                "title": movie_data["title"],
                                "genres": movie_data.get("genres", []),
                                "overview": movie_data.get("overview"),
                                "release_year": movie_data.get("release_year"),
                                "poster_path": movie_data.get("poster_path"),
                                "score": 0
                            }
                        }
                if mid in all_recommendations:
                    all_recommendations[mid]["scores"]["cf"] = score / 5.0  # Normalize to 0-1
        
        # 3. Semantic similarity (if text query or genres provided)
        if text_query or genres:
            semantic_recs = self._get_semantic_recommendations(
                text_query, genres, n_recommendations * 2
            )
            for rec in semantic_recs:
                mid = rec["movie_id"]
                if mid not in all_recommendations:
                    all_recommendations[mid] = {
                        "movie_id": mid,
                        "scores": {"cbf": 0, "cf": 0, "semantic": 0},
                        "data": rec
                    }
                all_recommendations[mid]["scores"]["semantic"] = rec["score"]
        
        # 4. Genre-based fallback
        if genres and len(all_recommendations) < n_recommendations:
            genre_recs = neo4j_service.search_movies(genres=genres, limit=n_recommendations)
            for rec in genre_recs:
                mid = rec["movie_id"]
                if mid not in all_recommendations:
                    all_recommendations[mid] = {
                        "movie_id": mid,
                        "scores": {"cbf": 0.3, "cf": 0, "semantic": 0.3},
                        "data": {
                            "movie_id": mid,
                            "title": rec["title"],
                            "genres": rec.get("genres", []),
                            "overview": rec.get("overview"),
                            "release_year": rec.get("release_year"),
                            "poster_path": rec.get("poster_path"),
                            "score": 0
                        }
                    }
        
        # Calculate final scores
        recommendations = []
        for mid, item in all_recommendations.items():
            # Skip movies already in the input
            if mid in movie_ids:
                continue
            
            # Weighted combination
            final_score = (
                self._cbf_weight * item["scores"]["cbf"] +
                self._cf_weight * item["scores"]["cf"] +
                self._semantic_weight * item["scores"]["semantic"]
            )
            
            # Boost if matches preferred genres
            if genres and item["data"].get("genres"):
                genre_overlap = len(set(genres) & set(item["data"]["genres"]))
                final_score *= (1 + 0.1 * genre_overlap)
            
            rec = item["data"].copy()
            rec["score"] = final_score
            rec["explanation"] = self._generate_explanation(item, genres)
            recommendations.append(rec)
        
        # Sort by score and return top N
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:n_recommendations]
    
    def _get_cbf_recommendations(
        self,
        movie_ids: List[int],
        text_query: Optional[str],
        n: int
    ) -> List[Dict[str, Any]]:
        """Get content-based recommendations."""
        recommendations = []
        
        # Get similar to each input movie
        for mid in movie_ids[:3]:  # Limit to avoid too many queries
            try:
                similar = self._cbf.get_similar(mid, n_recommendations=n // max(len(movie_ids), 1))
                recommendations.extend(similar)
            except Exception as e:
                logger.warning(f"CBF error for movie {mid}: {e}")
        
        # Get recommendations from text query
        if text_query:
            try:
                text_recs = self._cbf.get_recommendations_for_text(text_query, n_recommendations=n)
                recommendations.extend(text_recs)
            except Exception as e:
                logger.warning(f"CBF text query error: {e}")
        
        return recommendations
    
    def _get_cf_recommendations(
        self,
        user_id: int,
        n: int
    ) -> List[tuple]:
        """Get collaborative filtering recommendations."""
        try:
            return self._cf.get_recommendations_for_user(user_id, n_recommendations=n)
        except Exception as e:
            logger.warning(f"CF error for user {user_id}: {e}")
            return []
    
    def _get_semantic_recommendations(
        self,
        text_query: Optional[str],
        genres: List[str],
        n: int
    ) -> List[Dict[str, Any]]:
        """Get semantic similarity-based recommendations."""
        # Build query text
        query_parts = []
        if text_query:
            query_parts.append(text_query)
        if genres:
            query_parts.append(" ".join(genres))
        
        if not query_parts:
            return []
        
        query = " ".join(query_parts)
        
        try:
            # Generate embedding
            query_embedding = embedding_service.generate_embedding(query)
            
            # Search in Neo4j
            results = neo4j_service.vector_search(
                embedding=query_embedding,
                limit=n
            )
            
            return [
                {
                    "movie_id": r["movie_id"],
                    "title": r["title"],
                    "score": r["score"],
                    "genres": r.get("genres", []),
                    "overview": r.get("overview"),
                    "release_year": r.get("release_year"),
                    "poster_path": r.get("poster_path")
                }
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Semantic search error: {e}")
            return []
    
    def _generate_explanation(
        self,
        item: Dict[str, Any],
        preferred_genres: List[str]
    ) -> str:
        """Generate explanation for why a movie is recommended."""
        explanations = []
        scores = item["scores"]
        data = item["data"]
        
        # Content-based explanation
        if scores["cbf"] > 0.5:
            explanations.append("similar content to movies you like")
        
        # Collaborative filtering explanation
        if scores["cf"] > 0.5:
            explanations.append("popular among users with similar taste")
        
        # Semantic explanation
        if scores["semantic"] > 0.5:
            explanations.append("matches your search criteria")
        
        # Genre match explanation
        if preferred_genres and data.get("genres"):
            matching = set(preferred_genres) & set(data["genres"])
            if matching:
                explanations.append(f"features {', '.join(matching)}")
        
        if explanations:
            return "Recommended because it has " + " and ".join(explanations)
        
        return "Recommended based on popularity and relevance"

