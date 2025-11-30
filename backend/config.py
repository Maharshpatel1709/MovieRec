"""
Configuration management for MovieRec application.
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Neo4j Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "movierecpassword"
    
    # Vertex AI Configuration
    google_cloud_project: Optional[str] = None
    google_application_credentials: Optional[str] = None
    vertex_ai_location: str = "us-central1"
    
    # Application Settings
    debug: bool = True
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Model Settings
    use_mock_embeddings: bool = True
    embedding_dimension: int = 768
    
    # Data Paths
    data_dir: str = "data"
    raw_data_dir: str = "data/raw"
    processed_data_dir: str = "data/processed"
    models_dir: str = "data/models"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string to list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars like VITE_API_URL


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()

