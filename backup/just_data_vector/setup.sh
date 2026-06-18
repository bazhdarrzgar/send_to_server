#!/bin/bash

# KMC Knowledge Graph Setup Script

echo "🚀 Starting setup for KMC Knowledge Graph Pipeline..."

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install it first."
    exit 1
fi

# 2. Install Requirements
echo "📥 Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Docker and Neo4j Setup
echo "🐳 Checking Docker status..."
if ! command -v docker &> /dev/null; then
    echo "📥 Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    DOCKER_CMD="sudo docker"
    echo "✅ Docker installed. Using 'sudo docker' for this session."
else
    DOCKER_CMD="docker"
fi

echo "🚢 Setting up Neo4j container..."
if ! $DOCKER_CMD ps -a --format '{{.Names}}' | grep -q "^neo4j-kmc$"; then
    $DOCKER_CMD run -d \
        --name neo4j-kmc \
        -p 7474:7474 -p 7687:7687 \
        -e NEO4J_AUTH=neo4j/password \
        -e NEO4J_PLUGINS='["apoc"]' \
        --restart always \
        neo4j:latest
    echo "✅ Neo4j started. Access it at http://localhost:7474"
else
    echo "✅ Neo4j container 'neo4j-kmc' already exists."
    if [ "$($DOCKER_CMD inspect -f '{{.State.Running}}' neo4j-kmc)" != "true" ]; then
        echo "🔄 Starting Neo4j container..."
        $DOCKER_CMD start neo4j-kmc
    fi
fi

# 4. Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "⚠️ Ollama not found in PATH. Please install it from https://ollama.com"
else
    if ollama list | grep -q "gemma4:26b"; then
        echo "✅ Model gemma4:26b already exists in Ollama."
    else
        echo "🧠 Pulling Gemma model (gemma4:26b)..."
        ollama pull gemma4:26b
    fi
fi

# 5. Create .env template if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env template..."
    echo "NEO4J_URI=bolt://localhost:7687" > .env
    echo "NEO4J_USER=neo4j" >> .env
    echo "NEO4J_PASSWORD=password" >> .env
fi

echo "✅ Setup complete!"
echo "💡 You can now run the pipeline: 'python kg_generator.py'"
