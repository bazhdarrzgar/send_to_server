import json
import os
from tqdm import tqdm
from neo4j import GraphDatabase
from langchain_community.graphs import Neo4jGraph
from langchain_ollama import OllamaLLM
from dotenv import load_dotenv

# Load configurations
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:26b")
JSON_FILE = os.getenv("JSON_FILE", "kurdish_medical_corpus_kmc.json")

# Initialize Neo4j and LLM
graph = Neo4jGraph(url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD)
llm = OllamaLLM(model=OLLAMA_MODEL)

def extract_entities(text):
    """
    Uses the local LLM to extract Symptoms and Treatments from Kurdish medical text.
    Returns a dictionary with 'symptoms' and 'treatments' lists.
    """
    prompt = f"""
    Extract medical symptoms and treatments from the following Central Kurdish text.
    Provide the output in JSON format with keys 'symptoms' and 'treatments'.
    If none are found, return empty lists.
    Only return the JSON.

    Text: {text}
    """
    try:
        response = llm.invoke(prompt)
        # Clean the response to ensure it's valid JSON
        json_str = response.strip().replace('```json', '').replace('```', '')
        entities = json.loads(json_str)
        return entities
    except Exception as e:
        print(f"Error extracting entities: {e}")
        return {"symptoms": [], "treatments": []}

def ingest_data(limit=None):
    """
    Reads the JSON file and populates the Neo4j graph.
    'limit' can be used to process only a subset of the data.
    """
    print(f"Loading data from {JSON_FILE}...")
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if limit:
        data = data[:limit]
        print(f"Limiting to first {limit} entries.")

    print(f"Starting ingestion of {len(data)} items...")
    
    for item in tqdm(data):
        doc = item.get('document', {})
        instruction = item.get('instruction', '')
        response = item.get('response', '')
        item_id = item.get('id', '')
        
        # Extract entities from the response
        # Note: In a real run, this is the bottleneck. 
        # For demonstration/testing, we might skip or use a smaller model.
        entities = extract_entities(response)
        
        # Cypher query to build the graph
        query = """
        MERGE (d:Document {title: $title})
        SET d.source = $source, d.date = $date, d.domain = $domain
        
        MERGE (i:Instruction {id: $id})
        SET i.text = $inst
        
        MERGE (r:Response {text: $resp})
        
        MERGE (i)-[:RESULTED_IN]->(r)
        MERGE (r)-[:EXTRACTED_FROM]->(d)
        
        WITH r
        FOREACH (symp_name IN $symptoms |
            MERGE (s:Symptom {name: symp_name})
            MERGE (r)-[:MENTIONS_SYMPTOM]->(s)
        )
        
        WITH r
        FOREACH (treat_name IN $treatments |
            MERGE (t:Treatment {name: treat_name})
            MERGE (r)-[:HAS_TREATMENT]->(t)
        )
        """
        
        graph.query(query, params={
            "title": doc.get('title', 'Unknown'),
            "source": doc.get('source_url', ''),
            "date": doc.get('publication_date', ''),
            "domain": doc.get('domain', ''),
            "inst": instruction,
            "resp": response,
            "id": item_id,
            "symptoms": entities.get('symptoms', []),
            "treatments": entities.get('treatments', [])
        })

    print("\nGraph Ingestion Complete.")

if __name__ == "__main__":
    # You can change the limit to None to process all data (warning: takes a long time!)
    ingest_data(limit=100)
