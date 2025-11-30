"""
Knowledge Graph Neural Network (KGNN) Model.
Uses PyTorch Geometric for graph-based movie recommendations.
"""
import os
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from loguru import logger

from backend.config import settings
from backend.services.neo4j_service import neo4j_service

# Check if torch_geometric is available
try:
    from torch_geometric.nn import SAGEConv, GATConv
    from torch_geometric.data import Data
    TORCH_GEOMETRIC_AVAILABLE = True
except ImportError:
    TORCH_GEOMETRIC_AVAILABLE = False
    logger.warning("torch_geometric not available, using fallback KGNN")


class GraphSAGEModel(nn.Module):
    """GraphSAGE model for node embedding learning."""
    
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int = 128,
        out_channels: int = 64,
        num_layers: int = 2,
        dropout: float = 0.3
    ):
        super().__init__()
        
        self.convs = nn.ModuleList()
        self.convs.append(SAGEConv(in_channels, hidden_channels))
        
        for _ in range(num_layers - 2):
            self.convs.append(SAGEConv(hidden_channels, hidden_channels))
        
        self.convs.append(SAGEConv(hidden_channels, out_channels))
        self.dropout = dropout
    
    def forward(self, x, edge_index):
        for i, conv in enumerate(self.convs[:-1]):
            x = conv(x, edge_index)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
        
        x = self.convs[-1](x, edge_index)
        return x


class GATModel(nn.Module):
    """Graph Attention Network model."""
    
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int = 128,
        out_channels: int = 64,
        heads: int = 4,
        dropout: float = 0.3
    ):
        super().__init__()
        
        self.conv1 = GATConv(in_channels, hidden_channels, heads=heads, dropout=dropout)
        self.conv2 = GATConv(hidden_channels * heads, out_channels, heads=1, dropout=dropout)
        self.dropout = dropout
    
    def forward(self, x, edge_index):
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.conv1(x, edge_index)
        x = F.elu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.conv2(x, edge_index)
        return x


class SimpleMLP(nn.Module):
    """Simple MLP fallback when torch_geometric is not available."""
    
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int = 128,
        out_channels: int = 64
    ):
        super().__init__()
        self.fc1 = nn.Linear(in_channels, hidden_channels)
        self.fc2 = nn.Linear(hidden_channels, out_channels)
    
    def forward(self, x, edge_index=None):
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x


class KGNNModel:
    """KGNN model wrapper for training and inference."""
    
    def __init__(
        self,
        model_type: str = "graphsage",
        embedding_dim: int = 768,
        hidden_dim: int = 128,
        output_dim: int = 64
    ):
        self.model_type = model_type
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        
        self._model = None
        self._node_embeddings = None
        self._node_to_idx = {}
        self._idx_to_node = {}
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    def build_graph_from_neo4j(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Build graph data from Neo4j.
        Returns node features and edge index.
        """
        # Get edges from Neo4j
        edges_data = neo4j_service.get_graph_edges()
        
        # Get movie embeddings
        movie_embeddings = neo4j_service.get_movie_embeddings()
        
        # Build node index
        node_idx = 0
        nodes = set()
        
        # Add movie nodes
        for movie_id in movie_embeddings.keys():
            node_key = f"movie_{movie_id}"
            if node_key not in self._node_to_idx:
                self._node_to_idx[node_key] = node_idx
                self._idx_to_node[node_idx] = node_key
                node_idx += 1
                nodes.add(node_key)
        
        # Add other entity nodes from edges
        for edge_type, edge_list in edges_data.items():
            for edge in edge_list:
                source = f"{edge_type.split('_')[0]}_{edge['source']}"
                target = f"{edge_type.split('_')[1]}_{edge['target']}"
                
                for node in [source, target]:
                    if node not in self._node_to_idx:
                        self._node_to_idx[node] = node_idx
                        self._idx_to_node[node_idx] = node
                        node_idx += 1
        
        # Build edge index
        edge_sources = []
        edge_targets = []
        
        for edge_type, edge_list in edges_data.items():
            for edge in edge_list:
                source_key = f"{edge_type.split('_')[0]}_{edge['source']}"
                target_key = f"{edge_type.split('_')[1]}_{edge['target']}"
                
                if source_key in self._node_to_idx and target_key in self._node_to_idx:
                    # Add bidirectional edges
                    edge_sources.extend([
                        self._node_to_idx[source_key],
                        self._node_to_idx[target_key]
                    ])
                    edge_targets.extend([
                        self._node_to_idx[target_key],
                        self._node_to_idx[source_key]
                    ])
        
        # Build node features
        num_nodes = len(self._node_to_idx)
        node_features = np.random.randn(num_nodes, self.embedding_dim).astype(np.float32)
        
        # Set movie embeddings
        for movie_id, embedding in movie_embeddings.items():
            node_key = f"movie_{movie_id}"
            if node_key in self._node_to_idx:
                idx = self._node_to_idx[node_key]
                if len(embedding) == self.embedding_dim:
                    node_features[idx] = embedding
        
        # Normalize features
        node_features = node_features / (np.linalg.norm(node_features, axis=1, keepdims=True) + 1e-8)
        
        x = torch.FloatTensor(node_features)
        edge_index = torch.LongTensor([edge_sources, edge_targets]) if edge_sources else torch.LongTensor([[0], [0]])
        
        return x, edge_index
    
    def train(
        self,
        epochs: int = 100,
        lr: float = 0.01,
        weight_decay: float = 5e-4
    ):
        """Train the KGNN model."""
        logger.info("Building graph from Neo4j...")
        x, edge_index = self.build_graph_from_neo4j()
        
        if x.shape[0] == 0:
            logger.warning("No graph data available, using dummy model")
            self._create_dummy_embeddings()
            return
        
        x = x.to(self._device)
        edge_index = edge_index.to(self._device)
        
        # Create model
        if TORCH_GEOMETRIC_AVAILABLE:
            if self.model_type == "gat":
                self._model = GATModel(
                    in_channels=self.embedding_dim,
                    hidden_channels=self.hidden_dim,
                    out_channels=self.output_dim
                ).to(self._device)
            else:
                self._model = GraphSAGEModel(
                    in_channels=self.embedding_dim,
                    hidden_channels=self.hidden_dim,
                    out_channels=self.output_dim
                ).to(self._device)
        else:
            self._model = SimpleMLP(
                in_channels=self.embedding_dim,
                hidden_channels=self.hidden_dim,
                out_channels=self.output_dim
            ).to(self._device)
        
        optimizer = torch.optim.Adam(
            self._model.parameters(),
            lr=lr,
            weight_decay=weight_decay
        )
        
        logger.info(f"Training KGNN for {epochs} epochs...")
        self._model.train()
        
        for epoch in range(epochs):
            optimizer.zero_grad()
            
            # Forward pass
            embeddings = self._model(x, edge_index)
            
            # Self-supervised loss (reconstruct adjacency)
            if edge_index.shape[1] > 0:
                pos_edges = edge_index[:, :min(1000, edge_index.shape[1])]
                pos_out = torch.sigmoid((embeddings[pos_edges[0]] * embeddings[pos_edges[1]]).sum(dim=1))
                pos_loss = -torch.log(pos_out + 1e-8).mean()
                
                # Negative sampling
                neg_edges = torch.randint(0, x.shape[0], pos_edges.shape, device=self._device)
                neg_out = torch.sigmoid((embeddings[neg_edges[0]] * embeddings[neg_edges[1]]).sum(dim=1))
                neg_loss = -torch.log(1 - neg_out + 1e-8).mean()
                
                loss = pos_loss + neg_loss
            else:
                # Regularization loss when no edges
                loss = torch.norm(embeddings)
            
            loss.backward()
            optimizer.step()
            
            if (epoch + 1) % 20 == 0:
                logger.info(f"Epoch {epoch + 1}/{epochs}, Loss: {loss.item():.4f}")
        
        # Store learned embeddings
        self._model.eval()
        with torch.no_grad():
            self._node_embeddings = self._model(x, edge_index).cpu().numpy()
        
        logger.info("KGNN training complete")
    
    def _create_dummy_embeddings(self):
        """Create dummy embeddings when no data is available."""
        self._node_embeddings = np.random.randn(100, self.output_dim).astype(np.float32)
    
    def get_movie_embedding(self, movie_id: int) -> Optional[np.ndarray]:
        """Get learned embedding for a movie."""
        node_key = f"movie_{movie_id}"
        if node_key in self._node_to_idx and self._node_embeddings is not None:
            idx = self._node_to_idx[node_key]
            return self._node_embeddings[idx]
        return None
    
    def get_similar_movies(
        self,
        movie_id: int,
        n_recommendations: int = 10
    ) -> List[Tuple[int, float]]:
        """Get similar movies based on KGNN embeddings."""
        embedding = self.get_movie_embedding(movie_id)
        
        if embedding is None or self._node_embeddings is None:
            return []
        
        # Compute similarities with all movie nodes
        similarities = []
        for node_key, idx in self._node_to_idx.items():
            if node_key.startswith("movie_") and node_key != f"movie_{movie_id}":
                other_embedding = self._node_embeddings[idx]
                sim = np.dot(embedding, other_embedding) / (
                    np.linalg.norm(embedding) * np.linalg.norm(other_embedding) + 1e-8
                )
                mid = int(node_key.split("_")[1])
                similarities.append((mid, float(sim)))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:n_recommendations]
    
    def save(self, path: str):
        """Save the model to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        torch.save({
            "model_state": self._model.state_dict() if self._model else None,
            "node_embeddings": self._node_embeddings,
            "node_to_idx": self._node_to_idx,
            "idx_to_node": self._idx_to_node,
            "model_type": self.model_type,
            "embedding_dim": self.embedding_dim,
            "hidden_dim": self.hidden_dim,
            "output_dim": self.output_dim
        }, path)
        
        logger.info(f"KGNN model saved to {path}")
    
    @classmethod
    def load(cls, path: str) -> "KGNNModel":
        """Load a saved model."""
        data = torch.load(path, map_location="cpu")
        
        model = cls(
            model_type=data["model_type"],
            embedding_dim=data["embedding_dim"],
            hidden_dim=data["hidden_dim"],
            output_dim=data["output_dim"]
        )
        
        model._node_embeddings = data["node_embeddings"]
        model._node_to_idx = data["node_to_idx"]
        model._idx_to_node = data["idx_to_node"]
        
        logger.info(f"KGNN model loaded from {path}")
        return model


class KGNNRecommender:
    """KGNN-based movie recommender."""
    
    def __init__(self):
        self._model = None
        self._load_model()
    
    def _load_model(self):
        """Load pre-trained KGNN model or create new one."""
        model_path = os.path.join(settings.models_dir, "kgnn_model.pt")
        
        if os.path.exists(model_path):
            try:
                self._model = KGNNModel.load(model_path)
                return
            except Exception as e:
                logger.warning(f"Failed to load KGNN model: {e}")
        
        # Create new model (will use fallback if no data)
        self._model = KGNNModel()
    
    def recommend(
        self,
        user_id: Optional[int] = None,
        movie_ids: List[int] = None,
        n_recommendations: int = 10
    ) -> List[Dict[str, Any]]:
        """Get KGNN-based recommendations."""
        movie_ids = movie_ids or []
        
        if not movie_ids:
            # Return popular movies as fallback
            return neo4j_service.search_movies(limit=n_recommendations)
        
        # Aggregate recommendations from input movies
        all_similar = {}
        
        for mid in movie_ids[:5]:  # Limit input movies
            try:
                similar = self._model.get_similar_movies(mid, n_recommendations * 2)
                for sim_id, score in similar:
                    if sim_id not in movie_ids:  # Exclude input movies
                        if sim_id not in all_similar:
                            all_similar[sim_id] = []
                        all_similar[sim_id].append(score)
            except Exception as e:
                logger.warning(f"KGNN error for movie {mid}: {e}")
        
        # Average scores and get top recommendations
        scored_movies = [
            (mid, np.mean(scores))
            for mid, scores in all_similar.items()
        ]
        scored_movies.sort(key=lambda x: x[1], reverse=True)
        
        # Fetch movie details
        recommendations = []
        for mid, score in scored_movies[:n_recommendations]:
            movie = neo4j_service.get_movie_details(mid)
            if movie:
                recommendations.append({
                    "movie_id": mid,
                    "title": movie["title"],
                    "score": float(score),
                    "genres": movie.get("genres", []),
                    "overview": movie.get("overview"),
                    "release_year": movie.get("release_year"),
                    "poster_path": movie.get("poster_path")
                })
        
        # Fallback if no recommendations
        if not recommendations:
            return neo4j_service.search_movies(limit=n_recommendations)
        
        return recommendations

