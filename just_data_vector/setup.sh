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

# 4. Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "⚠️ Ollama not found in PATH. Please install it from https://ollama.com"
else
    echo "🧠 Pulling Gemma model (gemma4:26b)..."
    ollama pull gemma4:26b
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
