"""
Metadata endpoints for movies, actors, directors, etc.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from backend.services.neo4j_service import neo4j_service
from backend.services.graph_query_service import graph_query_service


router = APIRouter()

# Thread pool for parallel queries
_executor = ThreadPoolExecutor(max_workers=4)


class CastMember(BaseModel):
    """Cast member model."""
    id: int
    name: str
    character: Optional[str] = None
    profile_path: Optional[str] = None


class CrewMember(BaseModel):
    """Crew member model."""
    id: int
    name: str
    job: str
    department: Optional[str] = None


class SimilarMovie(BaseModel):
    """Similar movie in response."""
    movie_id: int
    title: str
    overview: Optional[str] = None
    release_year: Optional[int] = None
    vote_average: Optional[float] = None
    poster_path: Optional[str] = None
    genres: List[str] = []
    similarity_score: float = 0
    match_reason: Optional[str] = None


class MovieDetail(BaseModel):
    """Detailed movie information with similar movies."""
    movie_id: int
    title: str
    original_title: Optional[str] = None
    overview: Optional[str] = None
    release_date: Optional[str] = None
    release_year: Optional[int] = None
    runtime: Optional[int] = None
    budget: Optional[int] = None
    revenue: Optional[int] = None
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None
    popularity: Optional[float] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    genres: List[str] = []
    cast: List[CastMember] = []
    directors: List[CrewMember] = []
    keywords: List[str] = []
    similar_movies: List[SimilarMovie] = []


class ActorDetail(BaseModel):
    """Actor detail model."""
    id: int
    name: str
    profile_path: Optional[str] = None
    movies: List[Dict[str, Any]] = []
    known_for_genres: List[str] = []


class DirectorDetail(BaseModel):
    """Director detail model."""
    id: int
    name: str
    profile_path: Optional[str] = None
    movies: List[Dict[str, Any]] = []
    average_rating: Optional[float] = None


def _fetch_movie_details(movie_id: int) -> Optional[Dict[str, Any]]:
    """Helper to fetch movie details (runs in thread pool)."""
    return neo4j_service.get_movie_details(movie_id)


def _fetch_similar_movies(movie_id: int, limit: int = 6) -> List[Dict[str, Any]]:
    """Helper to fetch similar movies (runs in thread pool)."""
    try:
        similar_movies, _ = graph_query_service.find_similar_movies(
            movie_id=movie_id,
            limit=limit,
            genre_weight=5.0,
            actor_weight=3.0,
            director_weight=2.0,
            era_weight=1.0
        )
        return similar_movies
    except Exception as e:
        logger.error(f"Similar movies fetch error: {e}")
        return []


@router.get("/movie/{movie_id}", response_model=MovieDetail)
async def get_movie(
    movie_id: int,
    include_similar: bool = Query(default=True, description="Include similar movies"),
    similar_limit: int = Query(default=6, ge=1, le=20, description="Number of similar movies")
):
    """
    Get detailed information about a specific movie.
    Runs movie details and similar movies queries in PARALLEL for performance.
    """
    try:
        logger.info(f"Get movie details: {movie_id} (include_similar={include_similar})")
        
        # Submit both queries in parallel
        movie_future = _executor.submit(_fetch_movie_details, movie_id)
        similar_future = None
        if include_similar:
            similar_future = _executor.submit(_fetch_similar_movies, movie_id, similar_limit)
        
        # Wait for movie details first (required)
        movie = movie_future.result(timeout=10)
        
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        # Get similar movies result (optional)
        similar_movies_data = []
        if similar_future:
            try:
                similar_movies_data = similar_future.result(timeout=10)
            except Exception as e:
                logger.warning(f"Similar movies query failed: {e}")
        
        # Format similar movies
        similar_movies = [
            SimilarMovie(
                movie_id=m.get("movie_id"),
                title=m.get("title", ""),
                overview=(m.get("overview", "") or "")[:200],
                release_year=m.get("release_year"),
                vote_average=m.get("vote_average"),
                poster_path=m.get("poster_path"),
                genres=m.get("genres", []),
                similarity_score=m.get("similarity_score", 0),
                match_reason=m.get("_match_reason", "")
            )
            for m in similar_movies_data
            if m.get("movie_id")
        ]
        
        return MovieDetail(
            movie_id=movie["movie_id"],
            title=movie["title"],
            original_title=movie.get("original_title"),
            overview=movie.get("overview"),
            release_date=movie.get("release_date"),
            release_year=movie.get("release_year"),
            runtime=movie.get("runtime"),
            budget=movie.get("budget"),
            revenue=movie.get("revenue"),
            vote_average=movie.get("vote_average"),
            vote_count=movie.get("vote_count"),
            popularity=movie.get("popularity"),
            poster_path=movie.get("poster_path"),
            backdrop_path=movie.get("backdrop_path"),
            genres=movie.get("genres", []),
            cast=[CastMember(**c) for c in movie.get("cast", [])],
            directors=[CrewMember(**d) for d in movie.get("directors", [])],
            keywords=movie.get("keywords", []),
            similar_movies=similar_movies
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get movie error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actor/{actor_id}", response_model=ActorDetail)
async def get_actor(actor_id: int):
    """
    Get detailed information about an actor.
    """
    try:
        logger.info(f"Get actor details: {actor_id}")
        
        actor = neo4j_service.get_actor_details(actor_id)
        
        if not actor:
            raise HTTPException(status_code=404, detail="Actor not found")
        
        return ActorDetail(
            id=actor["id"],
            name=actor["name"],
            profile_path=actor.get("profile_path"),
            movies=actor.get("movies", []),
            known_for_genres=actor.get("known_for_genres", [])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get actor error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/director/{director_id}", response_model=DirectorDetail)
async def get_director(director_id: int):
    """
    Get detailed information about a director.
    """
    try:
        logger.info(f"Get director details: {director_id}")
        
        director = neo4j_service.get_director_details(director_id)
        
        if not director:
            raise HTTPException(status_code=404, detail="Director not found")
        
        return DirectorDetail(
            id=director["id"],
            name=director["name"],
            profile_path=director.get("profile_path"),
            movies=director.get("movies", []),
            average_rating=director.get("average_rating")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get director error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """
    Get database statistics.
    """
    try:
        stats = neo4j_service.get_database_stats()
        return stats
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
