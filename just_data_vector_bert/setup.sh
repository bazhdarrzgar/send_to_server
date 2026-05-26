#!/bin/bash

# KMC Vector Generation Setup Script

echo "🚀 Starting setup for KMC Vector Pipeline..."

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install it first."
    exit 1
fi

# 2. Install Requirements
echo "📥 Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Create .env template if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env template..."
    echo "MODEL_NAME=bert-large-cased" > .env
    echo "DATASET_PATH=../just_data_vector/kurdish_medical_corpus_kmc.json" >> .env
    echo "OUTPUT_PATH=kurdish_medical_vectors.jsonl" >> .env
fi

# 4. Download and Cache BERT Model
echo "🧠 Downloading and caching the 'bert-large-cased' model..."
python3 -c "
from transformers import AutoTokenizer, AutoModel
print('Downloading tokenizer...')
AutoTokenizer.from_pretrained('bert-large-cased')
print('Downloading model...')
AutoModel.from_pretrained('bert-large-cased')
print('Model cached successfully!')
"

echo "✅ Setup complete!"
echo "💡 You can now run the pipeline: 'python vector_generator.py'"
