# 🎬 MovieRec - AI-Powered Movie Recommendation System

A full-stack movie recommendation system built with Neo4j Knowledge Graph, KGNN (Knowledge Graph Neural Networks), RAG (Retrieval-Augmented Generation), and a modern React frontend.

![MovieRec Architecture](docs/architecture.png)

## ✨ Features

- **Hybrid Recommendations**: Combines content-based filtering (TF-IDF) and collaborative filtering (SVD/KNN)
- **Knowledge Graph**: Neo4j-powered graph with movies, actors, directors, and genres
- **Graph Neural Networks**: KGNN using PyTorch Geometric for learning graph embeddings
- **Semantic Search**: Vector similarity search using embeddings
- **RAG Chat**: Natural language movie recommendations with explanations
- **Beautiful UI**: Modern React frontend with chat interface and search

## 🏗️ Architecture

```
MovieRec/
├── backend/                 # FastAPI Python backend
│   ├── api/                # API routes
│   │   └── routes/         # Endpoint handlers
│   ├── models/             # ML models (CBF, CF, KGNN)
│   └── services/           # Business logic services
├── frontend/               # React + TypeScript frontend
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Page components
│   │   └── api/            # API client
├── scripts/                # Data processing scripts
├── data/                   # Data storage
│   ├── raw/               # Raw Kaggle data
│   ├── processed/         # Cleaned data
│   └── models/            # Trained models
└── docker-compose.yml     # Docker orchestration
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- (Optional) Kaggle account for movie data

### 1. Clone and Setup

```bash
cd MovieRec

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r backend/requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=movierecpassword

# Application Settings
DEBUG=true
USE_MOCK_EMBEDDINGS=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Vertex AI (Optional - mock mode if not set)
# GOOGLE_CLOUD_PROJECT=your-project-id
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### 3. Start Services

#### Option A: Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

#### Option B: Manual Start

Terminal 1 - Neo4j:
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/movierecpassword \
  neo4j:5.15.0
```

Terminal 2 - Backend:
```bash
cd MovieRec
source venv/bin/activate
uvicorn backend.api.main:app --reload --port 8000
```

Terminal 3 - Frontend:
```bash
cd MovieRec/frontend
npm run dev
```

### 4. Load Data

```bash
# Activate virtual environment
source venv/bin/activate

# Download or create sample data
python scripts/data_ingestion.py

# Preprocess data
python scripts/preprocess.py

# Build Neo4j graph
python scripts/graph_build.py

# Generate embeddings
python scripts/generate_embeddings.py

# Train models (optional - improves recommendations)
python scripts/train_models.py
```

### 5. Access the Application

- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474

## 📖 API Documentation

### Recommendation Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/recommend/hybrid` | POST | Hybrid recommendations (CBF + CF) |
| `/recommend/kgnn` | POST | KGNN-based recommendations |
| `/recommend/similar/{movie_id}` | GET | Similar movies to given movie |
| `/recommend/popular` | GET | Popular movies |

### Search Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search/semantic` | GET | Semantic vector search |
| `/search/movies` | GET | Text search with filters |
| `/search/genres` | GET | List all genres |

### RAG Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rag/query` | POST | RAG query with explanation |
| `/rag/chat` | POST | Conversational chat |
| `/rag/explain/{movie_id}` | GET | Explain movie recommendation |

### Metadata Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/metadata/movie/{movie_id}` | GET | Movie details |
| `/metadata/actor/{actor_id}` | GET | Actor details |
| `/metadata/director/{director_id}` | GET | Director details |
| `/metadata/stats` | GET | Database statistics |

## 🧠 ML Models

### Content-Based Filtering (CBF)
- TF-IDF vectorization of movie metadata
- Cosine similarity for recommendations
- Features: title, overview, genres

### Collaborative Filtering (CF)
- SVD matrix factorization
- KNN for user/item similarity
- Trained on user ratings

### Hybrid Recommender
- Weighted ensemble of CBF + CF + semantic search
- Configurable weights
- Genre boosting

### KGNN (Knowledge Graph Neural Network)
- GraphSAGE or GAT architecture
- Learns node embeddings from graph structure
- Captures relationships between entities

### RAG (Retrieval-Augmented Generation)
- Vector search retrieval from Neo4j
- LLM generation for explanations
- Mock mode for local development

## 🗄️ Data

The system uses "The Movies Dataset" from Kaggle:
https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset

Required files:
- `movies_metadata.csv` - Movie information
- `credits.csv` - Cast and crew
- `ratings_small.csv` - User ratings (for development)

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEO4J_URI` | Neo4j connection URI | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `movierecpassword` |
| `USE_MOCK_EMBEDDINGS` | Use mock embeddings | `true` |
| `DEBUG` | Enable debug mode | `true` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |

### Model Weights

Edit `backend/models/hybrid.py` to adjust:
```python
cbf_weight = 0.4      # Content-based filtering weight
cf_weight = 0.3       # Collaborative filtering weight
semantic_weight = 0.3  # Semantic similarity weight
```

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f backend

# Rebuild after code changes
docker-compose up -d --build

# Clear Neo4j data
docker-compose down -v
```

## 📝 Development

### Backend Development

```bash
# Run tests
pytest backend/

# Format code
black backend/

# Type checking
mypy backend/
```

### Frontend Development

```bash
cd frontend

# Development server
npm run dev

# Build for production
npm run build

# Lint
npm run lint
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- [The Movies Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) from Kaggle
- [Neo4j](https://neo4j.com/) for graph database
- [PyTorch Geometric](https://pytorch-geometric.readthedocs.io/) for GNN
- [FastAPI](https://fastapi.tiangolo.com/) for backend framework
- [React](https://react.dev/) for frontend framework

