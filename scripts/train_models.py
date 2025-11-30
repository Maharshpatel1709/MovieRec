"""
Model Training Script
Trains and saves all recommendation models.
"""
import os
import sys
from pathlib import Path

from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.models.cbf import ContentBasedFilter
from backend.models.cf import CollaborativeFilter
from backend.models.kgnn import KGNNModel


MODELS_DIR = Path(__file__).parent.parent / "data" / "models"


def train_cbf_model():
    """Train and save content-based filtering model."""
    logger.info("Training CBF model...")
    
    try:
        cbf = ContentBasedFilter()
        cbf._load_or_compute()
        
        os.makedirs(MODELS_DIR, exist_ok=True)
        cbf.save_model(str(MODELS_DIR / "cbf_model.pkl"))
        
        logger.info("CBF model trained and saved")
        return True
    except Exception as e:
        logger.error(f"CBF training failed: {e}")
        return False


def train_cf_model():
    """Train and save collaborative filtering model."""
    logger.info("Training CF model...")
    
    try:
        cf = CollaborativeFilter()
        cf._load_or_compute()
        
        os.makedirs(MODELS_DIR, exist_ok=True)
        cf.save_model(str(MODELS_DIR / "cf_model.pkl"))
        
        logger.info("CF model trained and saved")
        return True
    except Exception as e:
        logger.error(f"CF training failed: {e}")
        return False


def train_kgnn_model(epochs: int = 100):
    """Train and save KGNN model."""
    logger.info("Training KGNN model...")
    
    try:
        kgnn = KGNNModel()
        kgnn.train(epochs=epochs)
        
        os.makedirs(MODELS_DIR, exist_ok=True)
        kgnn.save(str(MODELS_DIR / "kgnn_model.pt"))
        
        logger.info("KGNN model trained and saved")
        return True
    except Exception as e:
        logger.error(f"KGNN training failed: {e}")
        return False


def main():
    """Main training pipeline."""
    logger.info("Starting model training...")
    
    results = {
        'cbf': train_cbf_model(),
        'cf': train_cf_model(),
        'kgnn': train_kgnn_model(epochs=50)
    }
    
    logger.info("\n=== Training Results ===")
    for model, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        logger.info(f"{model.upper()}: {status}")
    
    logger.info("Model training complete!")


if __name__ == "__main__":
    main()

