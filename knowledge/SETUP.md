# GraphRAG System for Kurdish Medical Corpus

This project implements a local GraphRAG (Graph Retrieval-Augmented Generation) system for the Central Kurdish (CKB) Medical Corpus using Neo4j and Ollama.

## Step 1: Install System Requirements

### 1.1 Install Neo4j (via Docker)
The easiest way to run Neo4j is using Docker. Run the following command:
```bash
docker run \
    --name neo4j-medical \
    -p 7474:7474 -p 7687:7687 \
    -d \
    -e NEO4J_AUTH=neo4j/password \
    -e NEO4J_PLUGINS='["apoc"]' \
    neo4j:latest
```
- Access the dashboard at: `http://localhost:7474`
- Username: `neo4j`
- Password: `password`

### 1.2 Install Ollama
Download and install Ollama from [ollama.com](https://ollama.com).
After installation, pull the required models:
```bash
ollama pull gemma4:26b
ollama pull nomic-embed-text
```

## Step 2: Setup Python Environment

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure your `.env` file matches your Neo4j credentials (it is already set up in this project).

## Step 3: Run Ingestion

The ingestion script reads the JSON corpus, extracts **Symptoms** and **Treatments** using Ollama, and populates the Neo4j graph.

Run the ingestion:
```bash
python ingest.py
```
*Note: By default, `ingest.py` is set to process the first 100 items for testing. You can modify the `limit` in the file to process more.*

## Step 4: Run Queries

Use the `query.py` script to ask questions in Kurdish. It uses a hybrid search (Graph + Vector) to find the most accurate information.

```bash
python query.py
```

## How it Works
1. **Nodes**: `Document`, `Instruction`, `Response`, `Symptom`, `Treatment`.
2. **Relationships**: 
   - `(Instruction)-[:RESULTED_IN]->(Response)`
   - `(Response)-[:EXTRACTED_FROM]->(Document)`
   - `(Response)-[:MENTIONS_SYMPTOM]->(Symptom)`
   - `(Response)-[:HAS_TREATMENT]->(Treatment)`
3. **Retrieval**: When you ask a question, the system searches the graph for specific medical entities and performs a semantic search on the text responses.
4. **Synthesis**: Gemma 4 combines the findings into a natural Kurdish response.
