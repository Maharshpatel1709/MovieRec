"""
ML Models Module
"""
from backend.models.cbf import ContentBasedFilter
from backend.models.cf import CollaborativeFilter
from backend.models.hybrid import HybridRecommender
from backend.models.kgnn import KGNNModel, KGNNRecommender

__all__ = [
    "ContentBasedFilter",
    "CollaborativeFilter", 
    "HybridRecommender",
    "KGNNModel",
    "KGNNRecommender"
]

