# 🛠️ Setup Guide: KMC Knowledge Graph

Follow these steps to set up the Knowledge Graph extraction pipeline on your server.

## 1. Prerequisites
- **Python 3.10+**
- **Ollama**: [Download & Install](https://ollama.com)
- **Neo4j**: Either a local installation, a Docker container, or Neo4j Aura.

## 2. Automatic Setup
Run the provided bash script to automate dependency installation, Docker/Neo4j setup, and model pulling:
```bash
chmod +x setup.sh
./setup.sh
```
The script will:
- Install Python dependencies.
- **Install Docker** (if missing).
- **Run Neo4j** in a container named `neo4j-kmc`.
- Pull the necessary LLM model via Ollama.

## 3. Manual Configuration

### Environment Variables
Edit the `.env` file with your specific Neo4j credentials:
```env
NEO4J_URI=bolt://your_server_ip:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
```

### Neo4j with Docker (Optional)
If you don't have Neo4j installed, you can run it easily with Docker:
```bash
docker run \
    --name neo4j-kmc \
    -p 7474:7474 -p 7687:7687 \
    -d \
    -e NEO4J_AUTH=neo4j/password \
    neo4j:latest
```

## 4. Running the Pipeline
Once configured, run the generator:
```bash
python kg_generator.py
```

## 5. Visualizing Results
1. Open Neo4j Browser (usually at `http://localhost:7474`).
2. Login with your credentials.
3. Run the following Cypher query to see your Kurdish Medical Knowledge Graph:
   ```cypher
   MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50
   ```
