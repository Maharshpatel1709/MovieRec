"""
RAG (Retrieval-Augmented Generation) endpoints.
Now with smart routing between graph and semantic search.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from loguru import logger

from backend.services.smart_rag_service import smart_rag_service


router = APIRouter()


class RAGQuery(BaseModel):
    """RAG query request model."""
    query: str = Field(..., min_length=1, max_length=1000)
    context_limit: int = Field(default=10, ge=1, le=20)
    include_reasoning: bool = Field(default=True)


class RetrievedContext(BaseModel):
    """Retrieved context item."""
    movie_id: int
    title: str
    relevance_score: float
    snippet: str
    metadata: Dict[str, Any] = {}


class RAGResponse(BaseModel):
    """RAG response model."""
    query: str
    answer: str
    recommendations: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=1000)
    history: List[ChatMessage] = Field(default_factory=list)
    context_limit: int = Field(default=10, ge=1, le=20)


class ChatResponse(BaseModel):
    """Chat response model."""
    message: str
    recommendations: List[Dict[str, Any]]
    suggestions: List[str]
    metadata: Optional[Dict[str, Any]] = None
    reasoning: Optional[Dict[str, Any]] = None  # Detailed explanation of how results were found


@router.post("/query", response_model=RAGResponse)
async def rag_query(request: RAGQuery):
    """
    Process a natural language query using smart RAG.
    
    This endpoint:
    1. Classifies the query intent (director/actor/genre/semantic)
    2. Routes to appropriate search (graph, semantic, or both)
    3. Merges and ranks results
    4. Generates a natural language response
    """
    try:
        logger.info(f"RAG query: '{request.query}'")
        
        response = await smart_rag_service.process_query(
            query=request.query,
            context_limit=request.context_limit
        )
        
        return RAGResponse(
            query=request.query,
            answer=response["answer"],
            recommendations=response["recommendations"],
            metadata=response.get("metadata") if request.include_reasoning else None
        )
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for conversational movie recommendations.
    
    Features:
    - Smart intent detection (no LLM needed)
    - Fast graph queries for structured requests
    - Semantic search for vague/descriptive queries
    - Parallel execution for speed
    """
    try:
        logger.info(f"Chat message: '{request.message}'")
        
        response = await smart_rag_service.chat(
            message=request.message,
            history=[(msg.role, msg.content) for msg in request.history],
            context_limit=request.context_limit
        )
        
        return ChatResponse(
            message=response["answer"],
            recommendations=response["recommendations"],
            suggestions=response["suggestions"],
            metadata=response.get("metadata"),
            reasoning=response.get("reasoning")
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/explain/{movie_id}")
async def explain_recommendation(movie_id: int, context: Optional[str] = None):
    """
    Generate an explanation for why a movie might be recommended.
    """
    try:
        from backend.services.graph_query_service import graph_query_service
        from backend.services.neo4j_service import neo4j_service
        
        logger.info(f"Explain recommendation for movie_id: {movie_id}")
        
        # Get movie details
        movie = neo4j_service.get_movie_details(movie_id)
        
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        # Get related movies
        related = graph_query_service.get_related_movies(movie_id, limit=5)
        
        # Build explanation
        explanation_parts = []
        key_features = []
        
        if movie.get("genres"):
            genres = ", ".join(movie["genres"])
            explanation_parts.append(f"**{movie['title']}** is a {genres} film")
            key_features.extend(movie["genres"])
        
        if movie.get("directors"):
            directors = ", ".join([d["name"] for d in movie["directors"][:2]])
            explanation_parts.append(f"directed by {directors}")
            key_features.append(f"Directed by {directors}")
        
        if movie.get("release_year"):
            explanation_parts.append(f"released in {movie['release_year']}")
        
        if movie.get("vote_average"):
            explanation_parts.append(f"with a rating of {movie['vote_average']:.1f}/10")
            key_features.append(f"Rating: {movie['vote_average']:.1f}/10")
        
        if movie.get("cast"):
            actors = ", ".join([c["name"] for c in movie["cast"][:3]])
            explanation_parts.append(f"starring {actors}")
            key_features.append(f"Starring: {actors}")
        
        explanation = ". ".join(explanation_parts) + "."
        
        if movie.get("overview"):
            explanation += f"\n\n{movie['overview']}"
        
        return {
            "movie_id": movie_id,
            "explanation": explanation,
            "key_features": key_features,
            "similar_movies": [
                {
                    "movie_id": r["movie_id"],
                    "title": r["title"],
                    "year": r.get("release_year")
                }
                for r in related[:3]
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Explain recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache")
async def clear_cache():
    """Clear the response cache."""
    smart_rag_service.clear_cache()
    return {"status": "Cache cleared"}
