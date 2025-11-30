"""
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from backend.config import settings
from backend.api.routes import recommend, search, rag, metadata, health
from backend.services.neo4j_service import neo4j_service
from backend.services.model_service import model_service


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting MovieRec API...")
    
    # Initialize Neo4j connection
    try:
        neo4j_service.connect()
        logger.info("Neo4j connection established")
    except Exception as e:
        logger.warning(f"Neo4j connection failed: {e}. Running in degraded mode.")
    
    # Load ML models
    try:
        model_service.load_models()
        logger.info("ML models loaded successfully")
    except Exception as e:
        logger.warning(f"Model loading failed: {e}. Some features may be unavailable.")
    
    logger.info("MovieRec API started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MovieRec API...")
    neo4j_service.close()
    logger.info("MovieRec API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="MovieRec API",
    description="Movie Recommendation System with Neo4j, KGNN, and RAG",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(recommend.router, prefix="/recommend", tags=["Recommendations"])
app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(rag.router, prefix="/rag", tags=["RAG"])
app.include_router(metadata.router, prefix="/metadata", tags=["Metadata"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "MovieRec API",
        "version": "1.0.0",
        "description": "Movie Recommendation System",
        "docs": "/docs",
        "health": "/health"
    }

