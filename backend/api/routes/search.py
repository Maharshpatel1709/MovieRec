"""
Search endpoints.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from loguru import logger

from backend.services.neo4j_service import neo4j_service
from backend.services.graph_query_service import graph_query_service
from backend.services.gemini_query_service import gemini_query_service, QueryType


router = APIRouter()


class MovieSearchResult(BaseModel):
    """Movie search result model."""
    movie_id: int
    title: str
    similarity_score: float
    genres: List[str] = []
    overview: Optional[str] = None
    release_year: Optional[int] = None
    poster_path: Optional[str] = None
    vote_average: Optional[float] = None
    match_reason: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response model."""
    results: List[MovieSearchResult]
    query: str
    total: int
    search_type: str
    detected_entities: Optional[dict] = None


@router.get("/smart", response_model=SearchResponse)
async def smart_search(
    query: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(default=20, ge=1, le=50)
):
    """
    Smart search powered by Gemini AI.
    - Uses Gemini to parse natural language queries
    - Generates and executes optimized Cypher queries
    - Handles unsupported queries gracefully
    """
    try:
        logger.info(f"Smart search: query='{query}', limit={limit}")
        
        # Parse query with Gemini
        parsed = gemini_query_service.parse_query(query)
        logger.info(f"Parsed: type={parsed.query_type.value}, entities={parsed.extracted_entities}")
        
        results = []
        search_type = parsed.query_type.value
        
        # Handle unsupported queries
        if not parsed.is_supported:
            return SearchResponse(
                results=[],
                query=query,
                total=0,
                search_type="unsupported",
                detected_entities={
                    "reason": parsed.unsupported_reason,
                    "explanation": parsed.explanation
                }
            )
        
        entities = parsed.extracted_entities
        
        # Similarity search
        if parsed.query_type == QueryType.SIMILAR:
            movie_title = entities.get("similar_to_movie", "")
            if movie_title:
                similar_results, details = graph_query_service.find_similar_movies(
                    movie_title=movie_title,
                    limit=limit
                )
                for r in similar_results:
                    results.append({
                        **r,
                        "score": r.get("similarity_score", r.get("_similarity_score", 0.5)),
                        "match_reason": r.get("_match_reason", f"Similar to {movie_title}")
                    })
        
        # Director search
        elif entities.get("director"):
            director_results = graph_query_service.search_by_director(
                entities["director"],
                limit=limit,
                year_min=entities.get("year_min"),
                year_max=entities.get("year_max")
            )
            for r in director_results:
                results.append({
                    **r,
                    "score": 1.0,
                    "match_reason": f"Directed by {entities['director']}"
                })
        
        # Actor search
        elif entities.get("actor"):
            actor_results = graph_query_service.search_by_actor(
                entities["actor"],
                limit=limit
            )
            for r in actor_results:
                results.append({
                    **r,
                    "score": 1.0,
                    "match_reason": f"Starring {entities['actor']}"
                })
        
        # Genre search
        elif entities.get("genres"):
            genre_results = graph_query_service.search_by_genre(
                entities["genres"],
                limit=limit,
                year_min=entities.get("year_min"),
                year_max=entities.get("year_max")
            )
            for r in genre_results:
                results.append({
                    **r,
                    "score": 1.0,
                    "match_reason": f"Genre: {', '.join(entities['genres'])}"
                })
        
        # Year range search
        elif entities.get("year_min") or entities.get("year_max"):
            year_results = graph_query_service.search_by_year_range(
                entities.get("year_min", 1900),
                entities.get("year_max", 2030),
                limit=limit
            )
            for r in year_results:
                results.append({
                    **r,
                    "score": 1.0,
                    "match_reason": f"From {entities.get('year_min', '')}-{entities.get('year_max', '')}"
                })
        
        # Default: show popular movies
        else:
            text_results = neo4j_service.search_movies(query=query, limit=limit)
            for r in text_results:
                results.append({
                    **r,
                    "score": r.get("popularity", 0.5),
                    "match_reason": "Title match"
                })
            search_type = "text"
        
        # Format results
        search_results = [
            MovieSearchResult(
                movie_id=r["movie_id"],
                title=r["title"],
                similarity_score=r.get("score", r.get("vote_average", 0) / 10 if r.get("vote_average") else 0.5),
                genres=r.get("genres", []),
                overview=r.get("overview"),
                release_year=r.get("release_year"),
                poster_path=r.get("poster_path"),
                vote_average=r.get("vote_average"),
                match_reason=r.get("match_reason")
            )
            for r in results
        ]
        
        return SearchResponse(
            results=search_results,
            query=query,
            total=len(search_results),
            search_type=search_type,
            detected_entities=entities
        )
    except Exception as e:
        logger.error(f"Smart search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/movies", response_model=SearchResponse)
async def search_movies(
    query: str = Query(default="", max_length=200),
    genres: Optional[str] = Query(default=None),
    year_min: Optional[int] = Query(default=None, ge=1900, le=2030),
    year_max: Optional[int] = Query(default=None, ge=1900, le=2030),
    rating_min: Optional[float] = Query(default=None, ge=0, le=10),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    Search movies with text query and filters.
    """
    try:
        logger.info(f"Movie search: query='{query}', genres={genres}")
        
        # Parse genres
        genre_list = genres.split(",") if genres else None
        
        results = neo4j_service.search_movies(
            query=query,
            genres=genre_list,
            year_min=year_min,
            year_max=year_max,
            rating_min=rating_min,
            limit=limit,
            offset=offset
        )
        
        search_results = [
            MovieSearchResult(
                movie_id=r["movie_id"],
                title=r["title"],
                similarity_score=r.get("score", 1.0),
                genres=r.get("genres", []),
                overview=r.get("overview"),
                release_year=r.get("release_year"),
                poster_path=r.get("poster_path"),
                vote_average=r.get("vote_average")
            )
            for r in results
        ]
        
        return SearchResponse(
            results=search_results,
            query=query,
            total=len(search_results),
            search_type="filter"
        )
    except Exception as e:
        logger.error(f"Movie search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/genres")
async def get_genres():
    """
    Get all available genres.
    """
    try:
        genres = neo4j_service.get_all_genres()
        return {"genres": genres}
    except Exception as e:
        logger.error(f"Get genres error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=1, max_length=100)
):
    """
    Get search suggestions/autocomplete for movie titles.
    """
    try:
        suggestions = neo4j_service.get_title_suggestions(query, limit=8)
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/explore")
async def explore_movies(
    category: str = Query(default="popular"),
    limit: int = Query(default=20, ge=1, le=50)
):
    """
    Explore movies by category.
    Categories: popular, top_rated, recent, classic, hidden_gems
    """
    try:
        if category == "popular":
            results = neo4j_service.search_movies(limit=limit)
        elif category == "top_rated":
            results = neo4j_service.search_movies(rating_min=8.0, limit=limit)
        elif category == "recent":
            results = neo4j_service.search_movies(year_min=2020, limit=limit)
        elif category == "classic":
            results = neo4j_service.search_movies(year_max=1990, rating_min=7.5, limit=limit)
        elif category == "hidden_gems":
            # Good rating but lower popularity
            results = neo4j_service.search_movies(rating_min=7.0, limit=limit * 2)
            # Sort by rating, not popularity
            results = sorted(results, key=lambda x: x.get("vote_average", 0), reverse=True)[:limit]
        else:
            results = neo4j_service.search_movies(limit=limit)
        
        search_results = [
            MovieSearchResult(
                movie_id=r["movie_id"],
                title=r["title"],
                similarity_score=r.get("vote_average", 0) / 10,
                genres=r.get("genres", []),
                overview=r.get("overview"),
                release_year=r.get("release_year"),
                poster_path=r.get("poster_path"),
                vote_average=r.get("vote_average")
            )
            for r in results
        ]
        
        return SearchResponse(
            results=search_results,
            query=category,
            total=len(search_results),
            search_type="explore"
        )
    except Exception as e:
        logger.error(f"Explore error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
