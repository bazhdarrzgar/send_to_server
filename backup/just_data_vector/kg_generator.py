import json
import os
import re
import logging
from typing import List, Dict
from tqdm import tqdm
from ollama import Client
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("kg_pipeline.log"),
        logging.StreamHandler()
    ]
)

# Configuration
OLLAMA_MODEL = "gemma4:26b"
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
DATASET_PATH = "kurdish_medical_corpus_kmc.json"
CHECKPOINT_PATH = "processed_ids.txt"

class KMCKnowledgeGraph:
    def __init__(self):
        self.client = Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
        try:
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            # Verify connection
            self.driver.verify_connectivity()
            logging.info("Connected to Neo4j successfully.")
        except Exception as e:
            logging.error(f"Failed to connect to Neo4j: {e}")
            raise

        self.processed_ids = self._load_checkpoints()

    def _load_checkpoints(self) -> set:
        if os.path.exists(CHECKPOINT_PATH):
            with open(CHECKPOINT_PATH, 'r') as f:
                return set(line.strip() for line in f)
        return set()

    def _save_checkpoint(self, entry_id: str):
        with open(CHECKPOINT_PATH, 'a') as f:
            f.write(f"{entry_id}\n")
        self.processed_ids.add(entry_id)

    def close(self):
        self.driver.close()

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def extract_triples(self, text: str) -> List[Dict]:
        """
        Extracts triples with entity types for better Neo4j labeling.
        """
        prompt = f"""
        You are an expert medical data engineer. Extract a Knowledge Graph from the Kurdish text below.
        
        OUTPUT RULES:
        1. All text values (head, relation, tail) MUST be in Kurdish (ckb).
        2. Entity types (head_type, tail_type) MUST be one of these English labels: [Disease, Symptom, Treatment, Medication, Anatomy, Provider, Organization].
        
        Kurdish Text: {text}
        
        Desired JSON Format:
        [
            {{
                "head": "Kurdish Entity 1",
                "head_type": "English Label",
                "relation": "Kurdish Relationship",
                "tail": "Kurdish Entity 2",
                "tail_type": "English Label"
            }}
        ]
        
        Return ONLY valid JSON. If no medical relationships exist, return [].
        """
        
        try:
            response = self.client.generate(
                model=OLLAMA_MODEL, 
                prompt=prompt, 
                format="json",
                options={"temperature": 0.1, "top_p": 0.9}
            )
            
            content = response['response']
            if "```" in content:
                content = re.search(r'\[.*\]', content, re.DOTALL).group()
                
            triples = json.loads(content)
            return triples
        except Exception as e:
            logging.warning(f"Extraction failed for text: {text[:50]}... Error: {e}")
            return []

    def store_triple(self, triple: Dict):
        """
        Stores triples with dynamic labels.
        """
        head = triple.get('head')
        h_type = triple.get('head_type', 'Entity')
        rel = triple.get('relation', 'RELATED_TO').upper().replace(" ", "_")
        tail = triple.get('tail')
        t_type = triple.get('tail_type', 'Entity')
        
        if not head or not tail:
            return

        # Sanitize labels (Neo4j labels must be alphanumeric)
        h_label = re.sub(r'[^a-zA-Z0-9]', '', h_type) or "Entity"
        t_label = re.sub(r'[^a-zA-Z0-9]', '', t_type) or "Entity"
        
        # Sanitize relation
        rel = re.sub(r'[^a-zA-Z0-9_]', '', rel)

        with self.driver.session() as session:
            # Use dynamic labels in Cypher
            query = (
                f"MERGE (h:{h_label} {{name: $head}}) "
                f"MERGE (t:{t_label} {{name: $tail}}) "
                f"MERGE (h)-[r:{rel}]->(t) "
                "RETURN h, r, t"
            )
            session.run(query, head=head, tail=tail)

    def process_dataset(self):
        logging.info(f"Loading dataset from {DATASET_PATH}...")
        try:
            with open(DATASET_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logging.error(f"Could not load JSON: {e}")
            return

        logging.info(f"Processing {len(data)} entries. Found {len(self.processed_ids)} already processed.")
        
        for entry in tqdm(data):
            entry_id = entry.get('id')
            if not entry_id or entry_id in self.processed_ids:
                continue
                
            raw_text = entry.get('response', '')
            if not raw_text:
                self._save_checkpoint(entry_id)
                continue
                
            cleaned_text = self.clean_text(raw_text)
            triples = self.extract_triples(cleaned_text)
            
            if triples:
                for triple in triples:
                    self.store_triple(triple)
            
            self._save_checkpoint(entry_id)

        logging.info("Pipeline finished successfully.")

if __name__ == "__main__":
    kg = KMCKnowledgeGraph()
    try:
        kg.process_dataset()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user. Progress saved.")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        kg.close()
