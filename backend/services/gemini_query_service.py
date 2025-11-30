"""
Gemini-based Query Generation Service
Uses Google's Gemini API to intelligently parse user queries and generate Cypher queries.
"""
import os
import json
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. Using fallback query parser.")


class QueryType(Enum):
    """Types of queries we can handle."""
    DIRECTOR = "director"
    ACTOR = "actor"
    GENRE = "genre"
    SIMILAR = "similar"
    YEAR = "year"
    COMBINED = "combined"
    UNSUPPORTED = "unsupported"


@dataclass
class ParsedQuery:
    """Result of parsing a user query."""
    query_type: QueryType
    cypher_query: str
    parameters: Dict[str, Any]
    explanation: str
    is_supported: bool = True
    unsupported_reason: str = ""
    extracted_entities: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extracted_entities is None:
            self.extracted_entities = {}


# System prompt for Gemini
SYSTEM_PROMPT = """You are a movie query parser. Extract structured information from natural language queries about movies.

**YOUR PRIMARY JOB**: Understand what the user wants and extract the relevant entities (director, actor, genre, movie title, year).

**IMPORTANT GUIDELINES**:
1. Be FLEXIBLE with grammar and sentence structure. All these mean the same thing:
   - "movies directed by Zack Snyder"
   - "Zack Snyder movies" 
   - "films by zack snyder"
   - "zack snyder films"
   - "show me zack snyder's movies"
   - "what movies did zack snyder direct"

2. Extract ANY person name that appears to be a director or actor based on context:
   - "directed by X" / "by director X" → X is a director
   - "starring X" / "with X" / "featuring X" → X is an actor
   - "X movies" / "X films" → Could be director OR actor (use your knowledge)

3. FIX typos if you notice them, but don't reject queries just because of spelling:
   - "Cristopher Nolan" → "Christopher Nolan"
   - "Spielburg" → "Steven Spielberg"
   - "zak snyder" → "Zack Snyder"

4. Available genres: Action, Adventure, Animation, Comedy, Crime, Documentary, Drama, Family, Fantasy, History, Horror, Music, Mystery, Romance, Science Fiction, Thriller, War, Western

**SUPPORTED QUERIES** (return is_supported: true):
- Director queries: "movies directed by X", "X movies", "X's films"
- Actor queries: "movies with X", "X movies", "starring X"
- Genre queries: "horror movies", "action films", "sci-fi"
- Year/decade: "90s movies", "films from 2020", "movies between 2010-2020"
- Similar movies: "movies like Inception", "similar to The Matrix"
- Combinations: "Nolan sci-fi movies", "90s action with Schwarzenegger"

**UNSUPPORTED QUERIES** (return is_supported: false):
- Mood/feeling: "feel-good movies", "movies that make me cry"
- Plot details: "movies with twist endings", "where the hero dies"
- Subjective: "best movies", "underrated gems", "must-watch"
- Abstract: "mind-bending", "thought-provoking", "deep movies"

**RESPONSE FORMAT** (JSON only):
{
    "is_supported": true,
    "query_type": "director|actor|genre|similar|year|combined",
    "entities": {
        "director": "Full Name or null",
        "actor": "Full Name or null",
        "genres": ["Genre1", "Genre2"] or null,
        "similar_to_movie": "Movie Title or null",
        "year_min": 1990 or null,
        "year_max": 1999 or null,
        "rating_min": null
    },
    "explanation": "Brief description of what was understood",
    "unsupported_reason": ""
}

**EXAMPLES**:

User: "movies directed by zack snyder"
{"is_supported": true, "query_type": "director", "entities": {"director": "Zack Snyder", "actor": null, "genres": null, "similar_to_movie": null, "year_min": null, "year_max": null, "rating_min": null}, "explanation": "Movies directed by Zack Snyder", "unsupported_reason": ""}

User: "show me some tom hanks films"
{"is_supported": true, "query_type": "actor", "entities": {"director": null, "actor": "Tom Hanks", "genres": null, "similar_to_movie": null, "year_min": null, "year_max": null, "rating_min": null}, "explanation": "Movies starring Tom Hanks", "unsupported_reason": ""}

User: "i want to watch thriller movies from the 90s"
{"is_supported": true, "query_type": "combined", "entities": {"director": null, "actor": null, "genres": ["Thriller"], "similar_to_movie": null, "year_min": 1990, "year_max": 1999, "rating_min": null}, "explanation": "Thriller movies from 1990-1999", "unsupported_reason": ""}

User: "Cristopher Nolan movies"
{"is_supported": true, "query_type": "director", "entities": {"director": "Christopher Nolan", "actor": null, "genres": null, "similar_to_movie": null, "year_min": null, "year_max": null, "rating_min": null}, "explanation": "Movies by Christopher Nolan (corrected spelling)", "unsupported_reason": ""}

User: "movies that will make me cry"
{"is_supported": false, "query_type": "unsupported", "entities": {}, "explanation": "Mood-based query", "unsupported_reason": "I can't search by emotional impact. Try: 'drama movies' or 'romantic films'"}

User: "movies like Inseption"
Response: {"is_supported": true, "query_type": "similar", "entities": {"director": null, "actor": null, "genres": null, "similar_to_movie": "Inception", "year_min": null, "year_max": null, "rating_min": null}, "explanation": "Finding movies similar to Inception (corrected from Inseption)", "unsupported_reason": ""}

User: "Leanardo Dicaprio thriller movies"
Response: {"is_supported": true, "query_type": "combined", "entities": {"director": null, "actor": "Leonardo DiCaprio", "genres": ["Thriller"], "similar_to_movie": null, "year_min": null, "year_max": null, "rating_min": null}, "explanation": "Searching for thriller movies with Leonardo DiCaprio (corrected spelling)", "unsupported_reason": ""}

User: "movies that will make me cry"
Response: {"is_supported": false, "query_type": "unsupported", "entities": {}, "explanation": "This is a mood-based query", "unsupported_reason": "I can't search by emotional impact. Try: 'drama movies' or 'romantic movies' instead."}
"""


class GeminiQueryService:
    """
    Service that uses Gemini to parse natural language movie queries.
    """
    
    def __init__(self):
        self._model = None
        self._initialized = False
        self._api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    def _initialize(self):
        """Initialize Gemini model."""
        if self._initialized:
            return
        
        if not GEMINI_AVAILABLE:
            logger.warning("Gemini not available, using fallback")
            self._initialized = True
            return
        
        if not self._api_key:
            logger.warning("No Gemini API key found. Set GEMINI_API_KEY environment variable.")
            self._initialized = True
            return
        
        try:
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                }
            )
            logger.info("Gemini model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self._model = None
        
        self._initialized = True
    
    def parse_query(self, user_query: str) -> ParsedQuery:
        """
        Parse a user query using Gemini and return structured query info.
        
        Args:
            user_query: Natural language query from user
            
        Returns:
            ParsedQuery with extracted information and Cypher query
        """
        self._initialize()
        
        # Try Gemini first
        if self._model:
            try:
                result = self._parse_with_gemini(user_query)
                if result:
                    return result
            except Exception as e:
                logger.error(f"Gemini parsing failed: {e}")
        
        # Fallback to rule-based parsing
        return self._parse_with_rules(user_query)
    
    def _parse_with_gemini(self, user_query: str) -> Optional[ParsedQuery]:
        """Parse query using Gemini API."""
        prompt = f"{SYSTEM_PROMPT}\n\nUser query: \"{user_query}\"\n\nRespond with JSON only:"
        
        try:
            response = self._model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(response_text)
            
            # Build ParsedQuery from response
            is_supported = data.get("is_supported", True)
            query_type = QueryType(data.get("query_type", "unsupported"))
            entities = data.get("entities", {})
            explanation = data.get("explanation", "")
            unsupported_reason = data.get("unsupported_reason", "")
            
            if not is_supported:
                return ParsedQuery(
                    query_type=QueryType.UNSUPPORTED,
                    cypher_query="",
                    parameters={},
                    explanation=explanation,
                    is_supported=False,
                    unsupported_reason=unsupported_reason,
                    extracted_entities=entities
                )
            
            # Generate Cypher query based on entities
            cypher, params = self._generate_cypher(entities, query_type)
            
            return ParsedQuery(
                query_type=query_type,
                cypher_query=cypher,
                parameters=params,
                explanation=explanation,
                is_supported=True,
                extracted_entities=entities
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None
    
    def _generate_cypher(self, entities: Dict, query_type: QueryType) -> Tuple[str, Dict]:
        """Generate Cypher query from extracted entities."""
        params = {}
        match_clauses = []
        where_clauses = []
        
        # Director
        if entities.get("director"):
            match_clauses.append("(d:Director)-[:DIRECTED]->(m)")
            where_clauses.append("d.name =~ $director_pattern")
            params["director_pattern"] = f"(?i).*{entities['director']}.*"
        
        # Actor
        if entities.get("actor"):
            match_clauses.append("(a:Actor)-[:ACTED_IN]->(m)")
            where_clauses.append("a.name =~ $actor_pattern")
            params["actor_pattern"] = f"(?i).*{entities['actor']}.*"
        
        # Genres
        if entities.get("genres"):
            match_clauses.append("(m)-[:HAS_GENRE]->(g:Genre)")
            where_clauses.append("g.name IN $genres")
            params["genres"] = entities["genres"]
        
        # Year range
        if entities.get("year_min"):
            where_clauses.append("m.release_year >= $year_min")
            params["year_min"] = entities["year_min"]
        if entities.get("year_max"):
            where_clauses.append("m.release_year <= $year_max")
            params["year_max"] = entities["year_max"]
        
        # Rating
        if entities.get("rating_min"):
            where_clauses.append("m.vote_average >= $rating_min")
            params["rating_min"] = entities["rating_min"]
        
        # Build query
        if not match_clauses:
            match_clauses = ["(m:Movie)"]
        
        # Ensure Movie is in the pattern
        if not any("(m:Movie)" in c or "(m)" in c for c in match_clauses):
            match_clauses.insert(0, "(m:Movie)")
        
        match_str = "MATCH " + ", ".join(match_clauses).replace("(m), (m)", "(m)")
        where_str = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        cypher = f"""
        {match_str}
        {where_str}
        WITH DISTINCT m
        OPTIONAL MATCH (m)-[:HAS_GENRE]->(genre:Genre)
        WITH m, collect(DISTINCT genre.name) as genres
        RETURN 
            m.movie_id as movie_id,
            m.title as title,
            m.overview as overview,
            m.release_year as release_year,
            m.vote_average as vote_average,
            m.poster_path as poster_path,
            m.popularity as popularity,
            genres
        ORDER BY m.vote_average DESC, m.popularity DESC
        LIMIT 20
        """
        
        return cypher.strip(), params
    
    def _parse_with_rules(self, user_query: str) -> ParsedQuery:
        """Fallback rule-based parsing when Gemini is not available."""
        query_lower = user_query.lower()
        entities = {}
        query_type = QueryType.COMBINED
        
        # Common typo corrections (misspelling -> correct)
        typo_corrections = {
            # Directors
            "cristopher nolan": "christopher nolan",
            "cristopher": "christopher",
            "spielburg": "spielberg",
            "speilberg": "spielberg",
            "scorcese": "scorsese",
            "scorseze": "scorsese",
            "tarentino": "tarantino",
            "quenten": "quentin",
            "quintin": "quentin",
            "villneuv": "villeneuve",
            "villeneuv": "villeneuve",
            "ridley scot": "ridley scott",
            "tim burten": "tim burton",
            # Actors
            "leanardo": "leonardo",
            "dicapro": "dicaprio",
            "decaprio": "dicaprio",
            "schwarzeneger": "schwarzenegger",
            "schwarznegger": "schwarzenegger",
            "stallown": "stallone",
            "keano": "keanu",
            "tome hanks": "tom hanks",
            "johny depp": "johnny depp",
            # Movies
            "inseption": "inception",
            "inceptoin": "inception",
            "the dark nite": "the dark knight",
            "shawshank redemtion": "shawshank redemption",
            "the godfater": "the godfather",
            "pulp ficton": "pulp fiction",
        }
        
        # Apply typo corrections
        for typo, correct in typo_corrections.items():
            query_lower = query_lower.replace(typo, correct)
        
        # Check for unsupported patterns
        unsupported_patterns = [
            (r"make me (cry|laugh|happy|sad)", "mood-based query"),
            (r"feel.?good|uplifting|heartwarming", "mood-based query"),
            (r"twist ending|surprise ending", "plot-based query"),
            (r"underrated|overrated|hidden gem", "subjective quality query"),
            (r"mind.?bending|thought.?provoking", "abstract descriptor query"),
            (r"visually stunning|beautiful cinematography", "visual style query"),
            (r"about (redemption|love|death|life)", "thematic query"),
        ]
        
        for pattern, reason in unsupported_patterns:
            if re.search(pattern, query_lower):
                return ParsedQuery(
                    query_type=QueryType.UNSUPPORTED,
                    cypher_query="",
                    parameters={},
                    explanation=f"Detected {reason}",
                    is_supported=False,
                    unsupported_reason=f"I can't search by {reason}. Try searching by genre, director, actor, or year instead."
                )
        
        # Check for "directed by X" pattern first - extract any name after it
        directed_by_match = re.search(r'directed by\s+([a-z]+(?:\s+[a-z]+)*)', query_lower)
        if directed_by_match:
            director_name = directed_by_match.group(1).strip().title()
            entities["director"] = director_name
            query_type = QueryType.DIRECTOR
        
        # Extract director (known names + variations)
        known_directors = [
            ("christopher nolan", "Christopher Nolan"),
            ("nolan", "Christopher Nolan"),
            ("steven spielberg", "Steven Spielberg"),
            ("spielberg", "Steven Spielberg"),
            ("martin scorsese", "Martin Scorsese"),
            ("scorsese", "Martin Scorsese"),
            ("quentin tarantino", "Quentin Tarantino"),
            ("tarantino", "Quentin Tarantino"),
            ("james cameron", "James Cameron"),
            ("david fincher", "David Fincher"),
            ("fincher", "David Fincher"),
            ("ridley scott", "Ridley Scott"),
            ("denis villeneuve", "Denis Villeneuve"),
            ("villeneuve", "Denis Villeneuve"),
            ("wes anderson", "Wes Anderson"),
            ("stanley kubrick", "Stanley Kubrick"),
            ("kubrick", "Stanley Kubrick"),
            ("alfred hitchcock", "Alfred Hitchcock"),
            ("hitchcock", "Alfred Hitchcock"),
            ("tim burton", "Tim Burton"),
            ("zack snyder", "Zack Snyder"),
            ("snyder", "Zack Snyder"),
            ("michael bay", "Michael Bay"),
            ("bay", "Michael Bay"),
            ("peter jackson", "Peter Jackson"),
            ("george lucas", "George Lucas"),
            ("lucas", "George Lucas"),
            ("francis ford coppola", "Francis Ford Coppola"),
            ("coppola", "Francis Ford Coppola"),
            ("clint eastwood", "Clint Eastwood"),
            ("eastwood", "Clint Eastwood"),
            ("ron howard", "Ron Howard"),
            ("guy ritchie", "Guy Ritchie"),
            ("ritchie", "Guy Ritchie"),
            ("m night shyamalan", "M. Night Shyamalan"),
            ("shyamalan", "M. Night Shyamalan"),
            ("guillermo del toro", "Guillermo del Toro"),
            ("del toro", "Guillermo del Toro"),
            ("jj abrams", "J.J. Abrams"),
            ("abrams", "J.J. Abrams"),
            ("sam raimi", "Sam Raimi"),
            ("raimi", "Sam Raimi"),
            ("edgar wright", "Edgar Wright"),
            ("russo brothers", "Russo Brothers"),
            ("russo", "Russo Brothers"),
        ]
        for pattern, full_name in known_directors:
            if pattern in query_lower and not entities.get("director"):
                entities["director"] = full_name
                query_type = QueryType.DIRECTOR
                break
        
        # Check for "starring X" or "with X" pattern - extract actor name
        starring_match = re.search(r'(?:starring|with|featuring)\s+([a-z]+(?:\s+[a-z]+)*)', query_lower)
        if starring_match and not entities.get("actor"):
            actor_name = starring_match.group(1).strip().title()
            entities["actor"] = actor_name
            if query_type != QueryType.DIRECTOR:
                query_type = QueryType.ACTOR
        
        # Extract actor (known names + variations)
        known_actors = [
            ("tom hanks", "Tom Hanks"),
            ("hanks", "Tom Hanks"),
            ("leonardo dicaprio", "Leonardo DiCaprio"),
            ("dicaprio", "Leonardo DiCaprio"),
            ("leo dicaprio", "Leonardo DiCaprio"),
            ("brad pitt", "Brad Pitt"),
            ("pitt", "Brad Pitt"),
            ("tom cruise", "Tom Cruise"),
            ("cruise", "Tom Cruise"),
            ("morgan freeman", "Morgan Freeman"),
            ("freeman", "Morgan Freeman"),
            ("robert de niro", "Robert De Niro"),
            ("de niro", "Robert De Niro"),
            ("al pacino", "Al Pacino"),
            ("pacino", "Al Pacino"),
            ("will smith", "Will Smith"),
            ("denzel washington", "Denzel Washington"),
            ("washington", "Denzel Washington"),
            ("johnny depp", "Johnny Depp"),
            ("depp", "Johnny Depp"),
            ("christian bale", "Christian Bale"),
            ("bale", "Christian Bale"),
            ("matt damon", "Matt Damon"),
            ("damon", "Matt Damon"),
            ("scarlett johansson", "Scarlett Johansson"),
            ("johansson", "Scarlett Johansson"),
            ("jennifer lawrence", "Jennifer Lawrence"),
            ("meryl streep", "Meryl Streep"),
            ("streep", "Meryl Streep"),
            ("arnold schwarzenegger", "Arnold Schwarzenegger"),
            ("schwarzenegger", "Arnold Schwarzenegger"),
            ("sylvester stallone", "Sylvester Stallone"),
            ("stallone", "Sylvester Stallone"),
            ("keanu reeves", "Keanu Reeves"),
            ("reeves", "Keanu Reeves"),
            ("ryan gosling", "Ryan Gosling"),
            ("gosling", "Ryan Gosling"),
            ("chris hemsworth", "Chris Hemsworth"),
            ("hemsworth", "Chris Hemsworth"),
            ("robert downey jr", "Robert Downey Jr."),
            ("downey", "Robert Downey Jr."),
            ("chris evans", "Chris Evans"),
            ("samuel l jackson", "Samuel L. Jackson"),
            ("jackson", "Samuel L. Jackson"),
            ("dwayne johnson", "Dwayne Johnson"),
            ("the rock", "Dwayne Johnson"),
            ("jason statham", "Jason Statham"),
            ("statham", "Jason Statham"),
            ("vin diesel", "Vin Diesel"),
            ("diesel", "Vin Diesel"),
            ("margot robbie", "Margot Robbie"),
            ("robbie", "Margot Robbie"),
            ("gal gadot", "Gal Gadot"),
            ("gadot", "Gal Gadot"),
            ("henry cavill", "Henry Cavill"),
            ("cavill", "Henry Cavill"),
            ("ben affleck", "Ben Affleck"),
            ("affleck", "Ben Affleck"),
            ("jason momoa", "Jason Momoa"),
            ("momoa", "Jason Momoa"),
        ]
        for pattern, full_name in known_actors:
            if pattern in query_lower:
                entities["actor"] = full_name
                query_type = QueryType.ACTOR
                break
        
        # Extract genres
        genre_map = {
            "action": "Action", "comedy": "Comedy", "drama": "Drama",
            "horror": "Horror", "thriller": "Thriller", "sci-fi": "Science Fiction",
            "science fiction": "Science Fiction", "romance": "Romance",
            "adventure": "Adventure", "fantasy": "Fantasy", "animation": "Animation",
            "documentary": "Documentary", "mystery": "Mystery", "crime": "Crime",
            "war": "War", "western": "Western", "family": "Family", "musical": "Music"
        }
        found_genres = []
        for keyword, genre in genre_map.items():
            if keyword in query_lower:
                found_genres.append(genre)
        if found_genres:
            entities["genres"] = list(set(found_genres))
            if not entities.get("director") and not entities.get("actor"):
                query_type = QueryType.GENRE
        
        # Extract decade/year
        decade_match = re.search(r"(\d{2})s\b", query_lower)
        if decade_match:
            decade = int(decade_match.group(1))
            if decade < 30:
                entities["year_min"] = 2000 + decade
                entities["year_max"] = 2000 + decade + 9
            else:
                entities["year_min"] = 1900 + decade
                entities["year_max"] = 1900 + decade + 9
            query_type = QueryType.YEAR
        
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", query_lower)
        if year_match:
            year = int(year_match.group(1))
            entities["year_min"] = year
            entities["year_max"] = year
        
        # Check for "movies like X"
        similar_match = re.search(r"(?:movies?|films?) (?:like|similar to) [\"']?([^\"'\?]+)[\"']?", query_lower, re.IGNORECASE)
        if similar_match:
            entities["similar_to_movie"] = similar_match.group(1).strip()
            query_type = QueryType.SIMILAR
        
        # Generate Cypher
        cypher, params = self._generate_cypher(entities, query_type)
        
        explanation = self._build_explanation(entities)
        
        return ParsedQuery(
            query_type=query_type,
            cypher_query=cypher,
            parameters=params,
            explanation=explanation,
            is_supported=True,
            extracted_entities=entities
        )
    
    def _build_explanation(self, entities: Dict) -> str:
        """Build human-readable explanation of what was detected."""
        parts = []
        if entities.get("director"):
            parts.append(f"director: {entities['director']}")
        if entities.get("actor"):
            parts.append(f"actor: {entities['actor']}")
        if entities.get("genres"):
            parts.append(f"genres: {', '.join(entities['genres'])}")
        if entities.get("year_min") and entities.get("year_max"):
            if entities["year_min"] == entities["year_max"]:
                parts.append(f"year: {entities['year_min']}")
            else:
                parts.append(f"years: {entities['year_min']}-{entities['year_max']}")
        if entities.get("similar_to_movie"):
            parts.append(f"similar to: {entities['similar_to_movie']}")
        
        if parts:
            return "Searching for movies with " + ", ".join(parts)
        return "Searching all movies"


# Singleton instance
gemini_query_service = GeminiQueryService()

