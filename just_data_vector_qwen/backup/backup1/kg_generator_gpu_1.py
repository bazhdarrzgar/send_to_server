import json
import os
import re
import logging
import sys
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
        logging.FileHandler("kg_pipeline_gpu_1.log"),
        logging.StreamHandler()
    ]
)

# Configuration
OLLAMA_MODEL = "qwen3.6:35b"
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
DATASET_PATH = "kurdish_medical_corpus_kmc_part2.json"
CHECKPOINT_PATH = "processed_ids_gpu_1.txt"
OUTPUT_FILE = "extracted_triples_gpu_1.jsonl"

class KMCKnowledgeGraph:
    def __init__(self):
        # Explicitly set to port 11435 for GPU 1
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11435")
        self.client = Client(host=self.host)
        
        # Verify Ollama availability
        try:
            self.client.list()
            logging.info(f"Connected to Ollama successfully at {self.host}")
        except Exception as e:
            logging.error(f"Failed to connect to Ollama at {self.host}: {e}")
            sys.exit(1)

        try:
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            # Verify connection
            self.driver.verify_connectivity()
            logging.info("Connected to Neo4j successfully (GPU 1).")
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

    # ------------------------------------------------------------------
    # CENTRALISED OLLAMA CALLER
    # All model calls MUST go through this helper so that:
    #   • dict vs GenerateResponse object differences are handled once
    #   • <think>…</think> CoT blocks are always stripped (Qwen3)
    #   • empty-response is always caught and logged
    # Add new call sites here — never call self.client.generate() directly.
    # ------------------------------------------------------------------
    def _call_model(self, prompt: str, num_predict: int = 8192) -> str:
        """
        Calls Ollama and returns clean text with all think-tags removed.
        Returns an empty string on any failure.
        """
        # /no_think tells Qwen3 to skip Chain-of-Thought reasoning,
        # saving tokens and guaranteeing the JSON reply fits in the budget.
        full_prompt = "/no_think\n" + prompt
        try:
            res = self.client.generate(
                model=OLLAMA_MODEL,
                prompt=full_prompt,
                options={"temperature": 0.2, "num_predict": num_predict}
            )
            # Handle both plain dict and GenerateResponse object
            text = res.get('response', '') if isinstance(res, dict) else getattr(res, 'response', '')
            # Strip any residual <think>…</think> blocks (safety net)
            text = re.sub(r'<think>.*?</think>', '', text or '', flags=re.DOTALL).strip()
            return text
        except Exception as e:
            logging.error(f"_call_model error: {e}", exc_info=True)
            return ""

    def extract_triples(self, text: str, max_retries: int = 5) -> List[Dict]:
        """
        Extracts triples with a multi-stage self-correction loop:
        1. Extraction
        2. Self-Quality Assessment (Model determines if result is 'Excellent' or 'Poor')
        3. Mandatory Retry on empty results with explicit feedback.
        """
        last_feedback = ""
        
        for attempt in range(max_retries):
            # 1. GENERATION PHASE
            retry_nudge = ""
            if attempt > 0:
                if not last_feedback:
                    retry_nudge = "\n[SYSTEM ADVICE]: The last attempt was EMPTY. Use more specific medical relations and look closer at the Kurdish text."
                else:
                    retry_nudge = f"\n[CRITIQUE FROM PREVIOUS ATTEMPT]: {last_feedback}"

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
            {retry_nudge}
            """
            
            try:
                content = self._call_model(prompt, num_predict=8192)
                if not content:
                    logging.warning(f"Attempt {attempt+1}: Received empty response from model.")
                    continue
                    
                # 2. ROBUST JSON EXTRACTION (Handles Thinking/CoT tags)
                json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                else:
                    # Try to find anything between code blocks if regex fails
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()

                try:
                    data = json.loads(content)
                    # Handle various JSON structures
                    raw_triples = []
                    if isinstance(data, list):
                        raw_triples = data
                    elif isinstance(data, dict):
                        for key in ['triples', 'data', 'results', 'entities']:
                            if key in data and isinstance(data[key], list):
                                raw_triples = data[key]
                                break
                        if not raw_triples: raw_triples = [data]
                except Exception as je:
                    logging.warning(f"Attempt {attempt+1}: JSON Parse Error: {je}. Raw Content: {content[:100]}...")
                    continue

                # 2. VALIDATION & FORMATTING
                valid_triples = []
                for t in raw_triples:
                    if not isinstance(t, dict): continue
                    h = str(t.get('head', t.get('subject', ''))).strip()
                    ta = str(t.get('tail', t.get('object', ''))).strip()
                    r = str(t.get('relation', t.get('predicate', ''))).strip()
                    
                    if h and ta and r and len(h) > 1 and len(ta) > 1:
                        valid_triples.append({
                            "head": h, "head_type": str(t.get('head_type', 'Entity')),
                            "relation": r, "tail": ta, "tail_type": str(t.get('tail_type', 'Entity'))
                        })

                # 3. SELF-CORRECTION LOOP: Check if result is empty
                if not valid_triples:
                    logging.info(f"Attempt {attempt+1}: model returned zero valid triples. Text snippet: {text[:50]}...")
                    last_feedback = "" # Trigger the "empty" nudge
                    continue

                # 4. QUALITY GATE: Ask the model to verify its own work
                verification_prompt = f"""
                Review these medical triples extracted from the Kurdish text below:
                
                TEXT: {text}
                TRIPLES: {json.dumps(valid_triples, ensure_ascii=False)}
                
                Is this extraction PERFECT, ACCURATE, and in NATURAL KURDISH? 
                If any relation is generic ('is', 'has') or entities are missing, or if it feels low quality, reply 'POOR'.
                If it is medically accurate and high quality, reply 'EXCELLENT'.
                
                Output ONLY the word 'EXCELLENT' or 'POOR'.
                """
                
                v_content = self._call_model(verification_prompt, num_predict=512).upper()
                
                if "EXCELLENT" in v_content:
                    logging.info(f"Attempt {attempt+1}: Quality verified as EXCELLENT.")
                    return valid_triples
                else:
                    logging.warning(f"Attempt {attempt+1}: Quality check failed (POOR). Model feedback: {v_content}")
                    last_feedback = "The triples were marked as 'POOR' quality. Ensure relations are descriptive and all context is captured accurately in Kurdish."
                    
            except Exception as e:
                logging.error(f"Attempt {attempt+1} General Exception: {e}", exc_info=True)

        logging.error(f"Failed to extract triples for text after {max_retries} attempts. Returning empty.")
        return []

    def store_triple(self, triple: Dict):
        """
        Stores triples with dynamic labels.
        """
        try:
            head = triple.get('head')
            h_type = triple.get('head_type', 'Entity')
            rel = triple.get('relation', 'RELATED_TO').upper().replace(" ", "_").replace("-", "_")
            tail = triple.get('tail')
            t_type = triple.get('tail_type', 'Entity')
            
            if not head or not tail:
                return

            h_label = re.sub(r'[^a-zA-Z0-9]', '', str(h_type)) or "Entity"
            if h_label[0].isdigit(): h_label = "L_" + h_label
            
            t_label = re.sub(r'[^a-zA-Z0-9]', '', str(t_type)) or "Entity"
            if t_label[0].isdigit(): t_label = "L_" + t_label
            
            rel = re.sub(r'[^a-zA-Z0-9_]', '', str(rel)) or "RELATED_TO"
            if rel[0].isdigit(): rel = "R_" + rel

            with self.driver.session() as session:
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
            if not isinstance(entry, dict):
                continue

            entry_id = str(entry.get('id', '')) or str(entry.get('_id', ''))
            if not entry_id or entry_id in self.processed_ids:
                continue
                
            # Check multiple common field names for the text content
            raw_text = entry.get('response') or entry.get('instruction') or entry.get('content') or entry.get('text') or ''
            if not raw_text:
                self._save_checkpoint(entry_id)
                continue
                
            cleaned_text = self.clean_text(raw_text)
            triples = self.extract_triples(cleaned_text)
            
            # Save results to JSONL file immediately
            try:
                with open(OUTPUT_FILE, 'a', encoding='utf-8') as f_out:
                    record = {"id": entry_id, "triples": triples}
                    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f_out.flush() 
                    os.fsync(f_out.fileno()) 
            except Exception as e:
                logging.error(f"Failed to write to {OUTPUT_FILE}: {e}")

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
