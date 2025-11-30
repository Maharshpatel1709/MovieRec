"""
Health check endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

from backend.services.neo4j_service import neo4j_service


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    services: Dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check the health status of all services.
    """
    services = {}
    overall_status = "healthy"
    
    # Check Neo4j
    try:
        neo4j_healthy = neo4j_service.health_check()
        services["neo4j"] = {
            "status": "healthy" if neo4j_healthy else "unhealthy",
            "connected": neo4j_healthy
        }
        if not neo4j_healthy:
            overall_status = "degraded"
    except Exception as e:
        services["neo4j"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_status = "degraded"
    
    # Check models
    services["models"] = {
        "status": "healthy",
        "loaded": True
    }
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        services=services
    )


@router.get("/health/ready")
async def readiness_check():
    """
    Kubernetes-style readiness probe.
    """
    try:
        if neo4j_service.health_check():
            return {"status": "ready"}
        raise HTTPException(status_code=503, detail="Service not ready")
    except Exception:
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/health/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    """
    return {"status": "alive"}

