"""
Intent Classifier Service
Fast local classification of user queries to route to appropriate search method.
"""
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class SearchType(Enum):
    """Types of search strategies."""
    GRAPH = "graph"           # Structured graph query (director, actor, genre)
    SIMILAR = "similar"       # Graph-based similarity (movies like X)
    CBF = "cbf"               # Content-based filtering (TF-IDF text match)
    HYBRID = "hybrid"         # Graph + CBF combined
    FILTER = "filter"         # Simple filter-based search


@dataclass
class QueryIntent:
    """Parsed intent from user query."""
    search_types: List[SearchType] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    original_query: str = ""
    confidence: float = 0.0
    semantic_query: str = ""  # Cleaned query for CBF text matching
    similar_to_movie: str = ""  # Movie title for similarity search
    
    def needs_graph_search(self) -> bool:
        return SearchType.GRAPH in self.search_types or SearchType.HYBRID in self.search_types
    
    def needs_similarity_search(self) -> bool:
        return SearchType.SIMILAR in self.search_types
    
    def needs_cbf_search(self) -> bool:
        return SearchType.CBF in self.search_types or SearchType.HYBRID in self.search_types


class IntentClassifier:
    """
    Fast local intent classifier for movie queries.
    Uses pattern matching and keyword detection - no LLM needed.
    """
    
    # Director patterns - require explicit "directed by" phrases with proper names
    DIRECTOR_PATTERNS = [
        r"(?:directed|made|created) by (?:director )?([A-Z][a-z]+ [A-Z][a-z]+)",
        r"director ([A-Z][a-z]+ [A-Z][a-z]+)",
        r"by director ([A-Z][a-z]+ [A-Z][a-z]+)",
    ]
    
    # Actor patterns - require explicit "starring" phrases
    ACTOR_PATTERNS = [
        r"(?:starring|featuring) ([A-Z][a-z]+ [A-Z][a-z]+)",
        r"movies (?:with|starring) ([A-Z][a-z]+ [A-Z][a-z]+)",
        r"actor ([A-Z][a-z]+ [A-Z][a-z]+)",
    ]
    
    # Common adjectives that should NOT be parsed as names
    NON_NAME_WORDS = {
        "mind", "bending", "thriller", "action", "comedy", "horror", "scary",
        "funny", "great", "best", "good", "classic", "modern", "old", "new",
        "feel", "good", "bad", "fast", "slow", "long", "short", "high", "low",
        "dark", "light", "black", "white", "big", "small", "real", "fake",
        "thought", "provoking", "heart", "warming", "edge", "seat", "must",
        "watch", "highly", "rated", "award", "winning", "critically", "acclaimed",
    }
    
    # Genre keywords
    GENRE_KEYWORDS = {
        "action": ["action", "fight", "explosive", "combat"],
        "comedy": ["comedy", "funny", "hilarious", "laugh"],
        "drama": ["drama", "dramatic", "emotional"],
        "horror": ["horror", "scary", "terrifying", "frightening"],
        "sci-fi": ["sci-fi", "science fiction", "futuristic", "space"],
        "science fiction": ["science fiction", "sci-fi"],
        "romance": ["romance", "romantic", "love story"],
        "thriller": ["thriller", "suspense", "tense", "suspenseful"],
        "animation": ["animation", "animated", "cartoon"],
        "documentary": ["documentary", "real story", "true story"],
        "fantasy": ["fantasy", "magical", "mythical"],
        "adventure": ["adventure", "epic journey"],
        "mystery": ["mystery", "detective", "whodunit"],
        "crime": ["crime", "criminal", "heist"],
        "war": ["war", "military", "battlefield"],
        "western": ["western", "cowboy"],
        "family": ["family", "kids", "children"],
        "musical": ["musical", "singing", "songs"],
    }
    
    # "Movies like X" patterns - for graph similarity search
    SIMILAR_PATTERNS = [
        r"(?:movies?|films?) (?:like|similar to) [\"']?([^\"'\?]+)[\"']?",
        r"(?:something|anything) (?:like|similar to) [\"']?([^\"'\?]+)[\"']?",
        r"(?:similar|like) [\"']?([^\"'\?]+)[\"']?",
        r"(?:more|other) (?:movies?|films?) like [\"']?([^\"'\?]+)[\"']?",
        r"(?:if i liked?|i (?:love|loved|enjoy|enjoyed)) [\"']?([^\"'\?,]+)[\"']?",
        r"recommend.*(?:like|similar to) [\"']?([^\"'\?]+)[\"']?",
    ]
    
    # CBF/descriptive query indicators (replaces semantic)
    DESCRIPTIVE_KEYWORDS = [
        "suggest", "recommend", "something", "anything",
        "best", "top", "good", "great", "amazing",
        "underrated", "hidden gem", "classic",
        "mood", "feel", "vibe",
    ]
    
    # Year patterns
    YEAR_PATTERNS = [
        r"from (\d{4})",
        r"in (\d{4})",
        r"(\d{4}) movies",
        r"(\d{4})s",  # 1990s
        r"released (?:in )?(\d{4})",
    ]
    
    # Decade patterns
    DECADE_PATTERNS = [
        r"(\d{2})s movies",  # 90s movies
        r"from the (\d{2})s",
        r"(\d{4})s",  # 1990s
    ]
    
    # Known directors (for better matching)
    KNOWN_DIRECTORS = [
        "Christopher Nolan", "Steven Spielberg", "Martin Scorsese",
        "Quentin Tarantino", "James Cameron", "David Fincher",
        "Ridley Scott", "Denis Villeneuve", "Wes Anderson",
        "Coen Brothers", "Stanley Kubrick", "Alfred Hitchcock",
        "Francis Ford Coppola", "Tim Burton", "Peter Jackson",
        "Guillermo del Toro", "George Lucas", "Robert Zemeckis",
    ]
    
    # Known actors
    KNOWN_ACTORS = [
        "Tom Hanks", "Leonardo DiCaprio", "Brad Pitt",
        "Morgan Freeman", "Robert De Niro", "Al Pacino",
        "Tom Cruise", "Will Smith", "Denzel Washington",
        "Johnny Depp", "Christian Bale", "Matt Damon",
        "Scarlett Johansson", "Jennifer Lawrence", "Meryl Streep",
        "Natalie Portman", "Emma Stone", "Anne Hathaway",
    ]
    
    def classify(self, query: str) -> QueryIntent:
        """
        Classify a user query and extract intent.
        
        Args:
            query: User's natural language query
            
        Returns:
            QueryIntent with search types and extracted entities
        """
        intent = QueryIntent(original_query=query, semantic_query=query)
        query_lower = query.lower()
        
        # First check for "movies like X" pattern - highest priority
        similar_movie = self._extract_similar_movie(query)
        if similar_movie:
            intent.similar_to_movie = similar_movie
            intent.search_types = [SearchType.SIMILAR]
            intent.confidence = 0.95
            logger.info(f"Detected similarity query for movie: '{similar_movie}'")
            return intent
        
        # Track what we find
        found_director = self._extract_director(query)
        found_actor = self._extract_actor(query)
        found_genres = self._extract_genres(query_lower)
        found_year = self._extract_year(query)
        found_decade = self._extract_decade(query_lower)
        is_descriptive = self._is_descriptive_query(query_lower)
        
        # Set entities
        if found_director:
            intent.entities["director"] = found_director
        if found_actor:
            intent.entities["actor"] = found_actor
        if found_genres:
            intent.entities["genres"] = found_genres
        if found_year:
            intent.filters["year"] = found_year
        if found_decade:
            intent.filters["decade"] = found_decade
        
        # Determine search types
        has_structured = bool(found_director or found_actor or found_genres or found_year)
        
        if has_structured and is_descriptive:
            # Both structured and descriptive elements → Graph + CBF
            intent.search_types = [SearchType.HYBRID]
            intent.confidence = 0.9
            # Clean query for CBF text matching
            intent.semantic_query = self._clean_for_cbf(query, intent.entities)
        elif has_structured:
            # Pure structured query → Graph only
            intent.search_types = [SearchType.GRAPH]
            intent.confidence = 0.95
        elif is_descriptive:
            # Descriptive query without entities → CBF text matching
            intent.search_types = [SearchType.CBF]
            intent.confidence = 0.8
            intent.semantic_query = query
        else:
            # Default to Graph + CBF for unknown queries
            intent.search_types = [SearchType.HYBRID]
            intent.confidence = 0.5
            intent.semantic_query = query
        
        logger.debug(f"Classified query: {intent}")
        return intent
    
    def _extract_similar_movie(self, query: str) -> Optional[str]:
        """Extract movie title from 'movies like X' patterns."""
        for pattern in self.SIMILAR_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                movie_title = match.group(1).strip()
                # Clean up common trailing words
                movie_title = re.sub(r'\s+(but|and|with|that|which|please|thanks).*$', '', movie_title, flags=re.IGNORECASE)
                movie_title = movie_title.strip(' .,!?')
                if len(movie_title) >= 2:  # At least 2 chars for a valid title
                    return movie_title
        return None
    
    def _is_descriptive_query(self, query_lower: str) -> bool:
        """Check if query is descriptive and would benefit from CBF text matching."""
        return any(kw in query_lower for kw in self.DESCRIPTIVE_KEYWORDS)
    
    def _extract_director(self, query: str) -> Optional[str]:
        """Extract director name from query."""
        # First check known directors (case-insensitive)
        for director in self.KNOWN_DIRECTORS:
            if director.lower() in query.lower():
                return director
        
        # Then try patterns - NO case-insensitivity for name capture
        for pattern in self.DIRECTOR_PATTERNS:
            match = re.search(pattern, query)
            if match:
                name = match.group(1)
                if self._is_valid_name(name):
                    return name.title()
        
        return None
    
    def _extract_actor(self, query: str) -> Optional[str]:
        """Extract actor name from query."""
        # First check known actors (case-insensitive)
        for actor in self.KNOWN_ACTORS:
            if actor.lower() in query.lower():
                return actor
        
        # Then try patterns - NO case-insensitivity for name capture
        for pattern in self.ACTOR_PATTERNS:
            match = re.search(pattern, query)
            if match:
                name = match.group(1)
                if self._is_valid_name(name):
                    return name.title()
        
        return None
    
    def _is_valid_name(self, name: str) -> bool:
        """Check if the extracted string looks like a real name, not common words."""
        words = name.lower().split()
        # All words in the name should not be common non-name words
        for word in words:
            if word in self.NON_NAME_WORDS:
                return False
        # Name should have at least 2 parts (first and last)
        if len(words) < 2:
            return False
        return True
    
    def _extract_genres(self, query_lower: str) -> List[str]:
        """Extract genres from query."""
        found_genres = []
        for genre, keywords in self.GENRE_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                # Normalize genre name
                normalized = genre.title()
                if normalized == "Sci-Fi":
                    normalized = "Science Fiction"
                found_genres.append(normalized)
        return found_genres
    
    def _extract_year(self, query: str) -> Optional[int]:
        """Extract specific year from query."""
        for pattern in self.YEAR_PATTERNS:
            match = re.search(pattern, query)
            if match:
                year = int(match.group(1))
                if 1900 <= year <= 2030:
                    return year
        return None
    
    def _extract_decade(self, query_lower: str) -> Optional[Tuple[int, int]]:
        """Extract decade range from query."""
        # Handle "90s", "1990s", etc.
        match = re.search(r"(\d{2})s\b", query_lower)
        if match:
            decade_short = int(match.group(1))
            if decade_short < 30:  # 00s, 10s, 20s -> 2000s, 2010s, 2020s
                start_year = 2000 + decade_short
            else:  # 30s-90s -> 1930s-1990s
                start_year = 1900 + decade_short
            return (start_year, start_year + 9)
        
        match = re.search(r"(\d{4})s\b", query_lower)
        if match:
            start_year = int(match.group(1))
            return (start_year, start_year + 9)
        
        return None
    
    def _clean_for_cbf(self, query: str, entities: Dict) -> str:
        """Remove structured parts from query for cleaner CBF text matching."""
        cleaned = query
        
        # Remove director mentions
        if entities.get("director"):
            patterns = [
                rf"directed by (?:director )?{re.escape(entities['director'])}",
                rf"{re.escape(entities['director'])}(?:'s| movies| films)",
                rf"by {re.escape(entities['director'])}",
            ]
            for pattern in patterns:
                cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
        # Remove actor mentions
        if entities.get("actor"):
            patterns = [
                rf"(?:starring|with|featuring) {re.escape(entities['actor'])}",
                rf"{re.escape(entities['actor'])} movies",
            ]
            for pattern in patterns:
                cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
        # Clean up whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned if cleaned else query


# Singleton instance
intent_classifier = IntentClassifier()

