#!/bin/bash

# Configuration
VENV_DIR="venv"
REQUIREMENTS="requirements.txt"
MODEL_NAME="gemma4:26b"
EMBED_MODEL="nomic-embed-text"
INGEST_MARKER=".ingested"

echo "===================================================="
echo "   Kurdish Medical AI - Automation Script           "
echo "===================================================="

# 1. Virtual Environment Setup
if [ ! -d "$VENV_DIR" ]; then
    echo "STEP 1: Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo "STEP 1: Virtual environment already exists. Skipping."
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# 2. Install Dependencies
echo "STEP 2: Checking/Installing dependencies..."
pip install -r "$REQUIREMENTS"

# 3. Check Neo4j Connectivity (Basic check on port 7687)
echo "STEP 3: Checking Neo4j connection..."
if ! command -v nc &> /dev/null; then
    echo "Note: 'nc' (netcat) not found. Skipping port check. Ensuring Neo4j is running..."
else
    if nc -z localhost 7687; then
        echo "Neo4j is reachable."
    else
        echo "ERROR: Neo4j is not reachable on localhost:7687."
        echo "Please ensure your Docker container is running."
        exit 1
    fi
fi

# 4. Pull Ollama Models
echo "STEP 4: Ensuring Ollama models are pulled..."
if ollama list | grep -q "$MODEL_NAME"; then
    echo "Model $MODEL_NAME already exists."
else
    echo "Pulling $MODEL_NAME..."
    ollama pull "$MODEL_NAME"
fi

if ollama list | grep -q "$EMBED_MODEL"; then
    echo "Model $EMBED_MODEL already exists."
else
    echo "Pulling $EMBED_MODEL..."
    ollama pull "$EMBED_MODEL"
fi

# 5. Data Ingestion
if [ -f "$INGEST_MARKER" ]; then
    echo "STEP 5: Data already ingested (marker found). Skipping."
else
    echo "STEP 5: Running Data Ingestion (this may take time)..."
    python ingest.py
    if [ $? -eq 0 ]; then
        touch "$INGEST_MARKER"
        echo "Ingestion complete."
    else
        echo "ERROR during ingestion. Please check the logs."
        exit 1
    fi
fi

# 6. Launch Chat Interface
echo "STEP 6: Launching Agentic Chat Interface..."
echo "----------------------------------------------------"
python chat.py
