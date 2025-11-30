"""
RAG (Retrieval-Augmented Generation) service.
"""
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import re

from backend.services.neo4j_service import neo4j_service
from backend.services.embedding_service import embedding_service
from backend.config import settings


class RAGService:
    """Service for RAG-based movie recommendations and explanations."""
    
    def __init__(self):
        self._llm_client = None
        self._use_mock = True
    
    def _init_llm(self):
        """Initialize LLM client (Vertex AI or local)."""
        try:
            from vertexai.language_models import TextGenerationModel
            self._llm_client = TextGenerationModel.from_pretrained("text-bison@002")
            self._use_mock = False
            logger.info("Vertex AI LLM initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Vertex AI LLM: {e}")
            self._use_mock = True
    
    def _generate_mock_response(
        self,
        query: str,
        context: List[Dict[str, Any]]
    ) -> str:
        """Generate a mock response based on retrieved context."""
        if not context:
            return "I couldn't find any relevant movies for your query. Try being more specific about genres, themes, or similar movies you've enjoyed."
        
        # Build response from context
        movie_names = [c["title"] for c in context[:3]]
        
        # Extract themes from the query
        themes = self._extract_themes(query)
        
        response = f"Based on your interest in {themes if themes else 'movies'}, "
        
        if len(movie_names) == 1:
            response += f"I recommend **{movie_names[0]}**. "
        elif len(movie_names) == 2:
            response += f"I recommend **{movie_names[0]}** and **{movie_names[1]}**. "
        else:
            response += f"I recommend **{movie_names[0]}**, **{movie_names[1]}**, and **{movie_names[2]}**. "
        
        # Add details about first movie
        if context:
            first_movie = context[0]
            if first_movie.get("genres"):
                genres = ", ".join(first_movie["genres"][:3])
                response += f"These are {genres} films "
            if first_movie.get("overview"):
                response += f"that you might enjoy. {first_movie['overview'][:200]}..."
        
        return response
    
    def _extract_themes(self, query: str) -> str:
        """Extract themes from user query."""
        # Simple keyword extraction
        themes = []
        
        genre_keywords = {
            "action": "action",
            "comedy": "comedy",
            "drama": "drama",
            "horror": "horror",
            "sci-fi": "science fiction",
            "science fiction": "science fiction",
            "romance": "romance",
            "thriller": "thriller",
            "fantasy": "fantasy",
            "animation": "animation",
            "documentary": "documentary"
        }
        
        query_lower = query.lower()
        for keyword, theme in genre_keywords.items():
            if keyword in query_lower:
                themes.append(theme)
        
        # Check for director/actor mentions
        if "directed by" in query_lower or "director" in query_lower:
            themes.append("auteur films")
        if "starring" in query_lower or "with" in query_lower:
            themes.append("star-driven movies")
        
        return ", ".join(themes) if themes else ""
    
    async def process_query(
        self,
        query: str,
        context_limit: int = 5,
        include_reasoning: bool = True
    ) -> Dict[str, Any]:
        """
        Process a natural language query using RAG.
        """
        # Generate query embedding
        query_embedding = embedding_service.generate_embedding(query)
        
        # Retrieve relevant movies
        retrieved = neo4j_service.vector_search(
            embedding=query_embedding,
            limit=context_limit
        )
        
        # Build context
        context = []
        for movie in retrieved:
            context.append({
                "movie_id": movie["movie_id"],
                "title": movie["title"],
                "relevance_score": movie["score"],
                "snippet": movie.get("overview", "")[:300],
                "metadata": {
                    "genres": movie.get("genres", []),
                    "year": movie.get("release_year"),
                    "rating": movie.get("vote_average")
                }
            })
        
        # Generate response
        if self._use_mock or self._llm_client is None:
            self._init_llm()
        
        if self._llm_client and not self._use_mock:
            try:
                prompt = self._build_rag_prompt(query, context)
                response = self._llm_client.predict(prompt, max_output_tokens=500)
                answer = response.text
            except Exception as e:
                logger.warning(f"LLM generation failed: {e}")
                answer = self._generate_mock_response(query, context)
        else:
            answer = self._generate_mock_response(query, context)
        
        # Build recommendations
        recommendations = [
            {
                "movie_id": c["movie_id"],
                "title": c["title"],
                "score": c["relevance_score"],
                "genres": c["metadata"].get("genres", []),
                "year": c["metadata"].get("year"),
                "rating": c["metadata"].get("rating")
            }
            for c in context
        ]
        
        result = {
            "answer": answer,
            "recommendations": recommendations,
            "context": context
        }
        
        if include_reasoning:
            result["reasoning"] = self._generate_reasoning(query, context)
        
        return result
    
    def _build_rag_prompt(
        self,
        query: str,
        context: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for RAG generation."""
        context_str = "\n".join([
            f"- {c['title']} ({c['metadata'].get('year', 'N/A')}): {c['snippet']}"
            for c in context
        ])
        
        prompt = f"""You are a helpful movie recommendation assistant. Based on the user's query and the following relevant movies, provide a personalized recommendation with explanations.

User Query: {query}

Relevant Movies:
{context_str}

Please provide a natural, conversational response that:
1. Recommends 1-3 movies from the context
2. Explains why these movies match the user's interests
3. Mentions specific elements like directors, actors, themes, or style
4. Is engaging and informative

Response:"""
        
        return prompt
    
    def _generate_reasoning(
        self,
        query: str,
        context: List[Dict[str, Any]]
    ) -> str:
        """Generate reasoning for the recommendations."""
        if not context:
            return "No relevant movies found for the query."
        
        reasoning = f"Query analysis: '{query}'\n\n"
        reasoning += "Retrieved movies ranked by semantic similarity:\n"
        
        for i, c in enumerate(context, 1):
            reasoning += f"{i}. {c['title']} (score: {c['relevance_score']:.3f})\n"
            reasoning += f"   Genres: {', '.join(c['metadata'].get('genres', []))}\n"
        
        return reasoning
    
    async def chat(
        self,
        message: str,
        history: List[Tuple[str, str]],
        context_limit: int = 5
    ) -> Dict[str, Any]:
        """
        Process a chat message with conversation history.
        """
        # Build context from history
        conversation_context = ""
        for role, content in history[-5:]:  # Last 5 messages
            conversation_context += f"{role}: {content}\n"
        
        # Process as RAG query with conversation context
        full_query = f"{conversation_context}\nUser: {message}" if conversation_context else message
        
        result = await self.process_query(
            query=full_query,
            context_limit=context_limit,
            include_reasoning=False
        )
        
        # Generate follow-up suggestions
        suggestions = self._generate_suggestions(message, result["recommendations"])
        
        return {
            "message": result["answer"],
            "recommendations": result["recommendations"],
            "suggestions": suggestions
        }
    
    def _generate_suggestions(
        self,
        query: str,
        recommendations: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate follow-up query suggestions."""
        suggestions = []
        
        if recommendations:
            first_rec = recommendations[0]
            suggestions.append(f"Tell me more about {first_rec['title']}")
            
            if first_rec.get("genres"):
                genre = first_rec["genres"][0]
                suggestions.append(f"Show me more {genre} movies")
        
        suggestions.extend([
            "What are some critically acclaimed movies?",
            "Recommend something from the 90s",
            "What's good for a movie night with friends?"
        ])
        
        return suggestions[:4]
    
    async def explain_movie(
        self,
        movie_id: int,
        user_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an explanation for why a movie might be recommended.
        """
        # Get movie details
        movie = neo4j_service.get_movie_details(movie_id)
        
        if not movie:
            return {
                "explanation": "Movie not found.",
                "key_features": [],
                "similar_movies": []
            }
        
        # Build explanation
        explanation_parts = []
        key_features = []
        
        # Genres
        if movie.get("genres"):
            genres = ", ".join(movie["genres"])
            explanation_parts.append(f"**{movie['title']}** is a {genres} film")
            key_features.extend(movie["genres"])
        
        # Directors
        if movie.get("directors"):
            directors = ", ".join([d["name"] for d in movie["directors"][:2]])
            explanation_parts.append(f"directed by {directors}")
            key_features.append(f"Directed by {directors}")
        
        # Year and rating
        if movie.get("release_year"):
            explanation_parts.append(f"released in {movie['release_year']}")
        
        if movie.get("vote_average"):
            explanation_parts.append(f"with a rating of {movie['vote_average']:.1f}/10")
            key_features.append(f"Rating: {movie['vote_average']:.1f}/10")
        
        # Cast
        if movie.get("cast"):
            actors = ", ".join([c["name"] for c in movie["cast"][:3]])
            explanation_parts.append(f"starring {actors}")
            key_features.append(f"Starring: {actors}")
        
        explanation = ". ".join(explanation_parts) + "."
        
        if movie.get("overview"):
            explanation += f"\n\n{movie['overview']}"
        
        # Get similar movies
        similar = []
        if movie.get("genres"):
            similar_results = neo4j_service.search_movies(
                genres=movie["genres"][:2],
                limit=5
            )
            similar = [
                {
                    "movie_id": s["movie_id"],
                    "title": s["title"],
                    "year": s.get("release_year")
                }
                for s in similar_results
                if s["movie_id"] != movie_id
            ][:3]
        
        return {
            "explanation": explanation,
            "key_features": key_features,
            "similar_movies": similar
        }


# Singleton instance
rag_service = RAGService()

