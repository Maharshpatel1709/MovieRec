"""
Recommendation endpoints.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from loguru import logger

from backend.services.model_service import model_service
from backend.services.neo4j_service import neo4j_service


router = APIRouter()


class MovieRecommendation(BaseModel):
    """Movie recommendation model."""
    movie_id: int
    title: str
    score: float
    genres: List[str] = []
    poster_path: Optional[str] = None
    overview: Optional[str] = None
    release_year: Optional[int] = None
    explanation: Optional[str] = None


class RecommendationRequest(BaseModel):
    """Request model for recommendations."""
    user_id: Optional[int] = None
    movie_ids: List[int] = Field(default_factory=list)
    genres: List[str] = Field(default_factory=list)
    n_recommendations: int = Field(default=10, ge=1, le=50)


class RecommendationResponse(BaseModel):
    """Response model for recommendations."""
    recommendations: List[MovieRecommendation]
    method: str
    total: int


@router.post("/hybrid", response_model=RecommendationResponse)
async def get_hybrid_recommendations(request: RecommendationRequest):
    """
    Get hybrid recommendations combining content-based and collaborative filtering.
    """
    try:
        logger.info(f"Hybrid recommendation request: {request}")
        
        recommendations = model_service.get_hybrid_recommendations(
            user_id=request.user_id,
            movie_ids=request.movie_ids,
            genres=request.genres,
            n_recommendations=request.n_recommendations
        )
        
        return RecommendationResponse(
            recommendations=recommendations,
            method="hybrid",
            total=len(recommendations)
        )
    except Exception as e:
        logger.error(f"Hybrid recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kgnn", response_model=RecommendationResponse)
async def get_kgnn_recommendations(request: RecommendationRequest):
    """
    Get recommendations using Knowledge Graph Neural Network.
    """
    try:
        logger.info(f"KGNN recommendation request: {request}")
        
        recommendations = model_service.get_kgnn_recommendations(
            user_id=request.user_id,
            movie_ids=request.movie_ids,
            n_recommendations=request.n_recommendations
        )
        
        return RecommendationResponse(
            recommendations=recommendations,
            method="kgnn",
            total=len(recommendations)
        )
    except Exception as e:
        logger.error(f"KGNN recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/similar/{movie_id}", response_model=RecommendationResponse)
async def get_similar_movies(
    movie_id: int,
    n_recommendations: int = Query(default=10, ge=1, le=50)
):
    """
    Get movies similar to a given movie using content-based filtering.
    """
    try:
        logger.info(f"Similar movies request for movie_id: {movie_id}")
        
        recommendations = model_service.get_similar_movies(
            movie_id=movie_id,
            n_recommendations=n_recommendations
        )
        
        return RecommendationResponse(
            recommendations=recommendations,
            method="content_based",
            total=len(recommendations)
        )
    except Exception as e:
        logger.error(f"Similar movies error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/popular", response_model=RecommendationResponse)
async def get_popular_movies(
    n_recommendations: int = Query(default=10, ge=1, le=50),
    genre: Optional[str] = None
):
    """
    Get popular movies, optionally filtered by genre.
    """
    try:
        logger.info(f"Popular movies request: genre={genre}")
        
        recommendations = model_service.get_popular_movies(
            n_recommendations=n_recommendations,
            genre=genre
        )
        
        return RecommendationResponse(
            recommendations=recommendations,
            method="popularity",
            total=len(recommendations)
        )
    except Exception as e:
        logger.error(f"Popular movies error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

