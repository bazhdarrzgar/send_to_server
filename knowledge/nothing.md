> **Prompt:**
> "I am building a local GraphRAG system for a Central Kurdish (CKB) Medical Corpus using Neo4j and Ollama.
> **Data Structure:** I have JSON containing instructions, responses, and document metadata (source_url, domain, date).
> **Objective:**
> 1. Write a Python script using `langchain-community` and `neo4j` to parse this JSON and create a Knowledge Graph.
> 2. Define a schema where 'Symptoms' and 'Treatments' are extracted from the text as unique entities.
> 3. Implement a local retrieval chain using 'Gemma-4' via Ollama for reasoning and 'nomic-embed-text' for vector embeddings.
> 4. Ensure the system can answer questions by first searching the Neo4j graph for related nodes and then summarizing the findings in Central Kurdish."
> 
> 

---

### 2. The Training & Implementation Code

Since you want this 100% local, you don't "train" the base model from scratch (which costs thousands). Instead, you **Fine-Tune** the retrieval (RAG) and the Knowledge Graph.

#### Step 1: Install Dependencies

```bash
pip install langchain langchain-community neo4j ollama graphrag

```

#### Step 2: The GraphRAG Pipeline

This script connects your JSON data to your local Neo4j instance and prepares it for Gemma 4.

```python
import json
from neo4j import GraphDatabase
from langchain_community.llms import Ollama
from langchain_community.graphs import Neo4jGraph

# 1. Initialize Local Gemma 4
llm = Ollama(model="gemma4:26b") # Or use 'gemma4:4b' if you have lower VRAM

# 2. Connect to local Neo4j
graph = Neo4jGraph(
    url="bolt://localhost:7687", 
    username="neo4j", 
    password="password"
)

# 3. Ingestion Function
def ingest_medical_data(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for item in data:
        # Cypher query to build the graph
        query = """
        MERGE (d:Document {title: $title})
        SET d.source = $source, d.date = $date
        MERGE (i:Instruction {text: $inst, id: $id})
        MERGE (r:Response {text: $resp})
        MERGE (i)-[:RESULTED_IN]->(r)
        MERGE (r)-[:EXTRACTED_FROM]->(d)
        """
        graph.query(query, params={
            "title": item['document']['title'],
            "source": item['document']['source_url'],
            "date": item['document']['publication_date'],
            "inst": item['instruction'],
            "resp": item['response'],
            "id": item['id']
        })
    print("Graph Build Complete.")

# 4. Local GraphRAG Query
def ask_kurdish_medical_graph(question):
    # This uses the LLM to write a Cypher query to search the graph
    from langchain.chains import GraphCypherQAChain
    
    chain = GraphCypherQAChain.from_llm(llm, graph=graph, verbose=True)
    response = chain.run(question)
    return response

# Usage
# ingest_medical_data('your_data.json')
# print(ask_kurdish_medical_graph("ڕۆڵی پەرستاران لە خەستەخانەکان چییە؟"))

```

---

### 3. Understanding the System Architecture

To help you visualize how your local computer handles this without the cloud, here is the flow:

1. **Data Layer:** Your JSON files live on your SSD.
2. **Graph Layer:** Neo4j stores the *relationships* (e.g., this medicine treats this condition).
3. **Local Inference:** **Ollama** runs the **Gemma 4** weights using your GPU/RAM.
4. **Retrieval:** When you ask a question, the system doesn't just look for words; it "walks" the graph to find connected medical facts.

