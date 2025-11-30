#!/bin/bash

# MovieRec Setup Script
# This script sets up the entire Movie Recommendation System

set -e

echo "🎬 MovieRec Setup Script"
echo "========================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}Python not found. Please install Python 3.11+${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}Found Python $PYTHON_VERSION${NC}"

# Check Node.js
echo "Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}Found Node.js $NODE_VERSION${NC}"
else
    echo -e "${RED}Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi

# Check Docker
echo "Checking Docker..."
if command -v docker &> /dev/null; then
    echo -e "${GREEN}Docker found${NC}"
else
    echo -e "${YELLOW}Docker not found. Neo4j will need to be installed manually.${NC}"
fi

echo ""
echo "Setting up Python environment..."

# Create virtual environment
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo -e "${GREEN}Created virtual environment${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt

echo ""
echo "Setting up frontend..."

# Install frontend dependencies
cd frontend
npm install
cd ..

echo ""
echo "Creating data directories..."
mkdir -p data/raw data/processed data/models data/embeddings

# Copy env.example to .env if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        cp env.example .env
        echo -e "${GREEN}Created .env file from env.example${NC}"
    fi
fi

echo ""
echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Start Neo4j:"
echo "   docker-compose up -d neo4j"
echo ""
echo "2. Load sample data:"
echo "   source venv/bin/activate"
echo "   python scripts/data_ingestion.py"
echo "   python scripts/preprocess.py"
echo "   python scripts/graph_build.py"
echo ""
echo "3. Start the backend:"
echo "   uvicorn backend.api.main:app --reload"
echo ""
echo "4. Start the frontend (new terminal):"
echo "   cd frontend && npm run dev"
echo ""
echo "Or use Docker Compose to start everything:"
echo "   docker-compose up -d"
echo ""
echo "Access the app at: http://localhost:5173"
echo "API docs at: http://localhost:8000/docs"

