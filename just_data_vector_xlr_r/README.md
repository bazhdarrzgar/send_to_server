# KMC Vector Generation Pipeline

This project transforms the **Kurdish Medical Corpus (KMC)** into dense vector embeddings using the `xlm-roberta-base` model.

## Pipeline Architecture
1. **KMC Dataset**: Ingests JSON data from the source.
2. **Text Cleaning**: Sanitizes Kurdish medical text.
3. **Model Embeddings**: Uses `xlm-roberta-base` via Hugging Face Transformers to generate vector representations.
4. **Vector Storage**: Stores generated vectors in a JSONL file format (`kurdish_medical_vectors.jsonl`).

## Setup
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure Environment**:
   Settings are inside the script, but you can also define paths and model variants in `.env`.

## Usage
Run the generator script to start the vectorization process:
```bash
python vector_generator.py
```
