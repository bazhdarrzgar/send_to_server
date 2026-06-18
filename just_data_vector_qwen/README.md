# KMC Knowledge Graph Pipeline

This project transforms the **Kurdish Medical Corpus (KMC)** into a Knowledge Graph (Neo4j) focusing exclusively on entity relationships.

## Pipeline Architecture
1. **KMC Dataset**: Ingests JSON data.
2. **Text Cleaning**: Sanitizes Kurdish medical text.
3. **LLM NER & RE**: Uses `qwen3.6:35b` via Ollama to extract entities and relations.
4. **Triple Generation**: Formats results as `(Entity) -[Relation]-> (Entity)`.
5. **Knowledge Graph Storage**: Stores triples in **Neo4j**.

## Setup
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure Environment**:
   Create a `.env` file with your Neo4j credentials:
   ```env
   NEO4J_URI=bolt://your_server:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   ```
3. **Pull Model**:
   Ensure Ollama is running and pull the model:
   ```bash
   ollama pull qwen3.6:35b
   ```

## Usage
Run the generator script to start the extraction process:
```bash
python kg_generator.py
```

## Neo4j Visualization
Once processed, you can visualize the graph in Neo4j Browser using:
```cypher
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100
```
