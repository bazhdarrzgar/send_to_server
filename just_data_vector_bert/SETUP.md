# 🛠️ Setup Guide: KMC Vector Pipeline

This guide explains how to set up the mBERT vector embedding pipeline, how the files work together, and how to use the resulting data.

## 📁 File Overview & How They Work Together
- **`.env`**: Stores configuration variables like the model name (`bert-large-cased`) and dataset paths.
- **`requirements.txt`**: Lists the Python dependencies required (`transformers`, `torch`, `tqdm`).
- **`setup.sh`**: The main initializer. It checks for Python, installs the dependencies from `requirements.txt`, creates `.env` if missing, and downloads the `bert-large-cased` model to your local cache so it's ready.
- **`load_model_gpu_1.sh`**: An optional helper script. If you ever need to manually force-download or verify that the Hugging Face model is cached, you can run this.
- **`vector_generator.py`**: The core script. It reads your dataset (`kurdish_medical_corpus_kmc.json`), uses PyTorch and the cached mBERT model to convert text into mathematical arrays (dense vectors), and saves them to a file called `kurdish_medical_vectors.jsonl`.

## 1. Prerequisites
- **Python 3.10+**
- **NVIDIA GPU** (recommended for speed) with CUDA support.

## 2. Automatic Setup & Installation
Run the provided bash script to automate everything:
```bash
chmod +x setup.sh
./setup.sh
```

## 3. Running the Pipeline
Once the setup is complete and the model is downloaded, start the vector generation:
```bash
python vector_generator.py
```
This will create `kurdish_medical_vectors.jsonl` which contains the ID and the generated vector for each medical entry.

## 👁️ How and When to "View" the Results (Neo4j vs. Vectors)

### Can I view these like a graph in Neo4j?
**Not exactly in the same visual way.** 
- The previous pipeline (`gemma4`) created a **Knowledge Graph**, which extracts distinct relationships (e.g., `(Aspirin) -[TREATS]-> (Headache)`). This is highly visual and looks great as a graph in Neo4j Browser.
- This new pipeline (`bert-large-cased`) creates **Vector Embeddings**. A vector is a list of 1024 numbers that represents the *meaning* of the text. 

**However, you CAN still use Neo4j!**
Neo4j supports **Vector Search** (in versions 5.11+). Instead of looking at a visual web of nodes, you use vectors to perform AI-powered "Semantic Search". 

**Next Steps to use vectors in Neo4j:**
1. Once `vector_generator.py` finishes, you will have a `.jsonl` file.
2. You can write a script to insert these vectors as properties on Neo4j nodes.
3. You can then query Neo4j with a question (e.g., "What are treatments for fever?"), convert that question to a vector using the same XLM-R model, and ask Neo4j to find the nodes with the most similar vectors.

If your goal was simply to extract visual graph relationships, the `gemma4` script is the correct tool. If your goal is to build an AI semantic search engine (like a medical chatbot or RAG system), this vector pipeline is exactly what you need!
