"""
Data Preprocessing Script
Cleans and transforms raw movie data for the recommendation system.
"""
import os
import sys
import ast
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
import numpy as np
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Configuration
RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DATA_DIR = Path(__file__).parent.parent / "data" / "processed"


def safe_literal_eval(val):
    """Safely evaluate a string literal."""
    if pd.isna(val):
        return []
    try:
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return []


def extract_names(obj_list: List[Dict]) -> List[str]:
    """Extract names from a list of dictionaries."""
    if not isinstance(obj_list, list):
        return []
    return [item.get("name", "") for item in obj_list if isinstance(item, dict)]


def extract_ids(obj_list: List[Dict]) -> List[int]:
    """Extract IDs from a list of dictionaries."""
    if not isinstance(obj_list, list):
        return []
    return [item.get("id") for item in obj_list if isinstance(item, dict) and item.get("id")]


def parse_genres(genres_str) -> List[str]:
    """Parse genres from string representation."""
    genres_list = safe_literal_eval(genres_str)
    return extract_names(genres_list)


def clean_movies(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and preprocess movies metadata."""
    logger.info("Cleaning movies data...")
    
    # Filter out adult content
    if 'adult' in df.columns:
        df = df[df['adult'] != 'True'].copy()
    
    # Convert ID to integer
    df['id'] = pd.to_numeric(df['id'], errors='coerce')
    df = df.dropna(subset=['id'])
    df['id'] = df['id'].astype(int)
    
    # Parse genres
    if 'genres' in df.columns:
        df['genres'] = df['genres'].apply(parse_genres)
    else:
        df['genres'] = [[] for _ in range(len(df))]
    
    # Extract release year
    if 'release_date' in df.columns:
        df['release_year'] = pd.to_datetime(df['release_date'], errors='coerce').dt.year
    
    # Clean numeric columns
    numeric_cols = ['budget', 'revenue', 'runtime', 'popularity', 'vote_average', 'vote_count']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Clean text columns
    text_cols = ['title', 'original_title', 'overview', 'tagline']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna('')
            df[col] = df[col].astype(str).str.strip()
    
    # Select and rename columns
    columns_mapping = {
        'id': 'movie_id',
        'title': 'title',
        'original_title': 'original_title',
        'overview': 'overview',
        'tagline': 'tagline',
        'genres': 'genres',
        'release_date': 'release_date',
        'release_year': 'release_year',
        'runtime': 'runtime',
        'budget': 'budget',
        'revenue': 'revenue',
        'popularity': 'popularity',
        'vote_average': 'vote_average',
        'vote_count': 'vote_count',
        'poster_path': 'poster_path',
        'backdrop_path': 'backdrop_path',
        'original_language': 'original_language',
        'imdb_id': 'imdb_id'
    }
    
    available_cols = {k: v for k, v in columns_mapping.items() if k in df.columns}
    df = df[list(available_cols.keys())].rename(columns=available_cols)
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['movie_id'])
    
    # Filter movies with missing essential data
    df = df[df['title'].str.len() > 0]
    
    logger.info(f"Cleaned movies: {len(df)} records")
    return df


def process_credits(credits_df: pd.DataFrame) -> tuple:
    """Process credits data to extract actors and directors."""
    logger.info("Processing credits data...")
    
    actors = []
    directors = []
    movie_actors = []  # movie_id, actor_id relationships
    movie_directors = []  # movie_id, director_id relationships
    
    for _, row in credits_df.iterrows():
        movie_id = row.get('id')
        if pd.isna(movie_id):
            continue
        movie_id = int(movie_id)
        
        # Process cast
        cast_list = safe_literal_eval(row.get('cast', '[]'))
        for i, cast_member in enumerate(cast_list[:10]):  # Top 10 actors
            if isinstance(cast_member, dict):
                actor_id = cast_member.get('id')
                if actor_id:
                    actors.append({
                        'actor_id': actor_id,
                        'name': cast_member.get('name', ''),
                        'gender': cast_member.get('gender'),
                        'profile_path': cast_member.get('profile_path')
                    })
                    movie_actors.append({
                        'movie_id': movie_id,
                        'actor_id': actor_id,
                        'character': cast_member.get('character', ''),
                        'order': i
                    })
        
        # Process crew (directors)
        crew_list = safe_literal_eval(row.get('crew', '[]'))
        for crew_member in crew_list:
            if isinstance(crew_member, dict) and crew_member.get('job') == 'Director':
                director_id = crew_member.get('id')
                if director_id:
                    directors.append({
                        'director_id': director_id,
                        'name': crew_member.get('name', ''),
                        'gender': crew_member.get('gender'),
                        'profile_path': crew_member.get('profile_path')
                    })
                    movie_directors.append({
                        'movie_id': movie_id,
                        'director_id': director_id
                    })
    
    # Create DataFrames
    actors_df = pd.DataFrame(actors).drop_duplicates(subset=['actor_id'])
    directors_df = pd.DataFrame(directors).drop_duplicates(subset=['director_id'])
    movie_actors_df = pd.DataFrame(movie_actors)
    movie_directors_df = pd.DataFrame(movie_directors)
    
    logger.info(f"Processed: {len(actors_df)} actors, {len(directors_df)} directors")
    
    return actors_df, directors_df, movie_actors_df, movie_directors_df


def process_ratings(ratings_df: pd.DataFrame) -> pd.DataFrame:
    """Process ratings data."""
    logger.info("Processing ratings data...")
    
    # Ensure correct column names
    column_mapping = {
        'userId': 'user_id',
        'movieId': 'movie_id',
        'rating': 'rating',
        'timestamp': 'timestamp'
    }
    
    for old_name, new_name in column_mapping.items():
        if old_name in ratings_df.columns:
            ratings_df = ratings_df.rename(columns={old_name: new_name})
    
    # Convert types
    ratings_df['user_id'] = pd.to_numeric(ratings_df['user_id'], errors='coerce')
    ratings_df['movie_id'] = pd.to_numeric(ratings_df['movie_id'], errors='coerce')
    ratings_df['rating'] = pd.to_numeric(ratings_df['rating'], errors='coerce')
    
    # Remove invalid entries
    ratings_df = ratings_df.dropna(subset=['user_id', 'movie_id', 'rating'])
    ratings_df['user_id'] = ratings_df['user_id'].astype(int)
    ratings_df['movie_id'] = ratings_df['movie_id'].astype(int)
    
    logger.info(f"Processed ratings: {len(ratings_df)} records")
    return ratings_df


def extract_genres(movies_df: pd.DataFrame) -> pd.DataFrame:
    """Extract unique genres."""
    all_genres = set()
    for genres in movies_df['genres']:
        if isinstance(genres, list):
            all_genres.update(genres)
    
    genres_df = pd.DataFrame({'name': sorted(all_genres)})
    genres_df['genre_id'] = range(1, len(genres_df) + 1)
    
    logger.info(f"Extracted {len(genres_df)} unique genres")
    return genres_df


def create_movie_genres(movies_df: pd.DataFrame, genres_df: pd.DataFrame) -> pd.DataFrame:
    """Create movie-genre relationships."""
    genre_to_id = dict(zip(genres_df['name'], genres_df['genre_id']))
    
    relationships = []
    for _, movie in movies_df.iterrows():
        if isinstance(movie['genres'], list):
            for genre in movie['genres']:
                if genre in genre_to_id:
                    relationships.append({
                        'movie_id': movie['movie_id'],
                        'genre_id': genre_to_id[genre],
                        'genre_name': genre
                    })
    
    return pd.DataFrame(relationships)


def save_data(dataframes: Dict[str, pd.DataFrame]):
    """Save processed dataframes to CSV files."""
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    
    for name, df in dataframes.items():
        filepath = PROCESSED_DATA_DIR / f"{name}.csv"
        
        # Handle list columns for CSV export
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, list)).any():
                df[col] = df[col].apply(lambda x: ','.join(x) if isinstance(x, list) else x)
        
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {name}.csv ({len(df)} records)")


def main():
    """Main preprocessing pipeline."""
    logger.info("Starting data preprocessing...")
    
    # Load raw data
    try:
        movies_df = pd.read_csv(RAW_DATA_DIR / "movies_metadata.csv", low_memory=False)
        logger.info(f"Loaded movies_metadata.csv: {len(movies_df)} records")
    except Exception as e:
        logger.error(f"Failed to load movies_metadata.csv: {e}")
        return
    
    # Clean movies
    movies_df = clean_movies(movies_df)
    
    # Process credits if available
    actors_df = pd.DataFrame()
    directors_df = pd.DataFrame()
    movie_actors_df = pd.DataFrame()
    movie_directors_df = pd.DataFrame()
    
    try:
        credits_df = pd.read_csv(RAW_DATA_DIR / "credits.csv")
        actors_df, directors_df, movie_actors_df, movie_directors_df = process_credits(credits_df)
    except Exception as e:
        logger.warning(f"Credits data not available: {e}")
    
    # Process ratings if available
    ratings_df = pd.DataFrame()
    try:
        # Try full ratings first, fall back to small
        if (RAW_DATA_DIR / "ratings_small.csv").exists():
            ratings_df = pd.read_csv(RAW_DATA_DIR / "ratings_small.csv")
        elif (RAW_DATA_DIR / "ratings.csv").exists():
            ratings_df = pd.read_csv(RAW_DATA_DIR / "ratings.csv")
        
        if not ratings_df.empty:
            ratings_df = process_ratings(ratings_df)
    except Exception as e:
        logger.warning(f"Ratings data not available: {e}")
    
    # Extract genres
    genres_df = extract_genres(movies_df)
    movie_genres_df = create_movie_genres(movies_df, genres_df)
    
    # Save all processed data
    dataframes = {
        'movies': movies_df,
        'genres': genres_df,
        'movie_genres': movie_genres_df
    }
    
    if not actors_df.empty:
        dataframes['actors'] = actors_df
        dataframes['movie_actors'] = movie_actors_df
    
    if not directors_df.empty:
        dataframes['directors'] = directors_df
        dataframes['movie_directors'] = movie_directors_df
    
    if not ratings_df.empty:
        dataframes['ratings'] = ratings_df
    
    save_data(dataframes)
    
    # Print summary
    logger.info("\n=== Preprocessing Summary ===")
    logger.info(f"Movies: {len(movies_df)}")
    logger.info(f"Genres: {len(genres_df)}")
    logger.info(f"Actors: {len(actors_df)}")
    logger.info(f"Directors: {len(directors_df)}")
    logger.info(f"Ratings: {len(ratings_df)}")
    logger.info("Preprocessing complete!")


if __name__ == "__main__":
    main()

