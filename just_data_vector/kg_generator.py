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
OLLAMA_MODEL = "gemma4:31b"
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
DATASET_PATH = "kurdish_medical_corpus_kmc.json"
CHECKPOINT_PATH = "processed_ids.txt"
OUTPUT_FILE = "extracted_triples.jsonl"

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

    def extract_triples(self, text: str, max_retries: int = 5) -> List[Dict]:
        """
        Extracts triples with entity types for better Neo4j labeling.
        Implements a retry mechanism to ensure high-quality, non-empty medical data.
        """
        # Improved prompt with semantic guidance and quality focus
        prompt = f"""
        You are an elite Kurdish medical linguist and knowledge graph engineer. 
        Your task is to extract high-quality, semantically rich medical triples from the provided Kurdish text.

        CRITICAL QUALITY REQUIREMENTS:
        1. LANGUAGE: All medical entities and relationships MUST be in natural, accurate Kurdish (Sorani/Central Kurdish).
        2. MEANINGFUL RELATIONS: Avoid generic relations like 'has' or 'is'. Use precise medical verbs. 
           Examples: 
           - 'دەبێتە هۆی' (causes)
           - 'نیشانەیە بۆ' (is a symptom of)
           - 'بۆ یەکەمجار دەستنیشانکرا لە' (first diagnosed in)
           - 'بەکاردێت بۆ چارەسەری' (used for treatment of)
           - 'کاردەکاتە سەر' (affects)
           - 'بەشێکە لە' (is part of)
        3. ENTITY TYPES: 'head_type' and 'tail_type' MUST be exactly one of these English labels: [Disease, Symptom, Treatment, Medication, Anatomy, Provider, Organization].
        4. DATA INTEGRITY: Every triple MUST have a valid, descriptive 'head', 'relation', and 'tail'. No empty strings or generic placeholders.
        5. QUALITY ASSESSMENT: Only extract facts that are clearly stated. If a triple feels ambiguous or poor quality for the Kurdish language, discard it.

        Kurdish Text: {text}

        Requested JSON Format (List of Objects):
        [
            {{
                "head": "Entity Name in Kurdish",
                "head_type": "English Label",
                "relation": "Detailed Kurdish Relationship",
                "tail": "Target Entity in Kurdish",
                "tail_type": "English Label"
            }}
        ]

        Return ONLY valid JSON. If the text contains no meaningful medical relationships, return an empty list [].
        """
        
        for attempt in range(max_retries):
            try:
                response = self.client.generate(
                    model=OLLAMA_MODEL, 
                    prompt=prompt, 
                    format="json",
                    options={
                        "temperature": 0.3, # Increased for more descriptive relations
                        "top_p": 0.9,
                        "num_predict": 2048
                    }
                )
                
                if isinstance(response, dict):
                    content = response.get('response', '')
                else:
                    content = getattr(response, 'response', '')

                if not content:
                    continue
                    
                if "```" in content:
                    match = re.search(r'(\[.*\]|\{.*\})', content, re.DOTALL)
                    if match:
                        content = match.group(1)
                    
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    logging.warning(f"Attempt {attempt+1}: JSON Parse Error. Retrying...")
                    continue

                # Normalize to list
                if isinstance(data, dict):
                    raw_triples = [data]
                elif isinstance(data, list):
                    raw_triples = [item for item in data if isinstance(item, dict)]
                else:
                    continue

                # STRICT VALIDATION PASS
                valid_triples = []
                is_perfect_batch = True
                
                for t in raw_triples:
                    head = str(t.get('head', '')).strip()
                    tail = str(t.get('tail', '')).strip()
                    relation = str(t.get('relation', '')).strip()
                    
                    # Check for empty values or generic placeholders
                    if not head or not tail or not relation or len(head) < 2 or len(tail) < 2:
                        logging.info(f"Attempt {attempt+1}: Detected poor quality triple. Retrying batch...")
                        is_perfect_batch = False
                        break
                    
                    valid_triples.append({
                        "head": head,
                        "head_type": t.get('head_type', 'Entity'),
                        "relation": relation,
                        "tail": tail,
                        "tail_type": t.get('tail_type', 'Entity')
                    })

                if is_perfect_batch and valid_triples:
                    # Final check: are the relations meaningful? 
                    # If the LLM just gave us "has" or "is", we might want to nudge it, 
                    # but for now we accept non-empty descriptive text.
                    return valid_triples
                
                if not raw_triples and attempt == 0:
                    # If it's the first try and it found nothing, it might really be empty
                    return []

            except Exception as e:
                logging.warning(f"Attempt {attempt+1} Exception: {e}")
                
        return []

    def store_triple(self, triple: Dict):
        """
        Stores triples with dynamic labels.
        """
        try:
            head = triple.get('head')
            h_type = triple.get('head_type', 'Entity')
            rel = triple.get('relation', 'RELATED_TO').upper().replace(" ", "_")
            tail = triple.get('tail')
            t_type = triple.get('tail_type', 'Entity')
            
            if not head or not tail:
                return

            # Sanitize labels (Neo4j labels must be alphanumeric and not start with digits)
            h_label = re.sub(r'[^a-zA-Z0-9]', '', str(h_type)) or "Entity"
            if h_label[0].isdigit(): h_label = "L_" + h_label
            
            t_label = re.sub(r'[^a-zA-Z0-9]', '', str(t_type)) or "Entity"
            if t_label[0].isdigit(): t_label = "L_" + t_label
            
            # Sanitize relation
            rel = re.sub(r'[^a-zA-Z0-9_]', '', str(rel)) or "RELATED_TO"
            if rel[0].isdigit(): rel = "R_" + rel

            with self.driver.session() as session:
                # Use dynamic labels in Cypher
                query = (
                    f"MERGE (h:{h_label} {{name: $head}}) "
                    f"MERGE (t:{t_label} {{name: $tail}}) "
                    f"MERGE (h)-[r:{rel}]->(t) "
                    "RETURN h, r, t"
                )
                session.run(query, head=head, tail=tail)
        except Exception as e:
            logging.error(f"Failed to store triple in Neo4j: {triple}. Error: {e}")

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
                # Save to locally to JSONL file for inspection
                try:
                    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f_out:
                        record = {"id": entry_id, "triples": triples}
                        f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                except Exception as e:
                    logging.error(f"Failed to write to {OUTPUT_FILE}: {e}")

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
