import json
import os
import re
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional
from tqdm import tqdm
from ollama import Client
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ─────────────────────────────────────────────────────────
# GPU 0  →  Ollama on port 11434
# ─────────────────────────────────────────────────────────

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("kg_pipeline_gpu_0.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────
OLLAMA_HOST   = os.getenv("OLLAMA_HOST_GPU0", "http://localhost:11434")
OLLAMA_MODEL  = "qwen3.6:35b"
NEO4J_URI     = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER    = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD= os.getenv("NEO4J_PASSWORD", "password")
DATASET_PATH  = "kurdish_medical_corpus_kmc_part1.json"
CHECKPOINT_PATH = "processed_ids_gpu_0.txt"
OUTPUT_FILE   = "extracted_triples_gpu_0.jsonl"

# Qwen3 generation options – generous token budgets so CoT has room to breathe
OLLAMA_OPTIONS = {
    "temperature": 0.6,      # Qwen3 docs recommend 0.6 for balanced CoT
    "top_p": 0.95,           # Qwen3 recommended value
    "top_k": 20,             # Qwen3 recommended value
    "min_p": 0,
    "num_predict": 8192,     # Large budget: CoT + JSON output
    "num_ctx": 16384,        # Context window – enough for long Kurdish texts + prompt
    "repeat_penalty": 1.0,
}

# ── Robust JSON extractor ──────────────────────────────────
def _extract_json_from_text(text: str) -> Optional[list]:
    """
    Extract the first JSON array from arbitrary text (including CoT reasoning).
    Qwen3 thinks in <think>…</think> blocks before giving the answer;
    we must scan the *entire* response for any valid JSON array.
    """
    if not text:
        return None

    # Strip think blocks if present (Qwen3 CoT)
    text_no_think = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    # Prefer text after think block; fall back to full text
    sources = [text_no_think, text] if text_no_think else [text]

    for src in sources:
        # Try to find a JSON array directly
        for match in re.finditer(r'\[', src):
            start = match.start()
            depth = 0
            for i, ch in enumerate(src[start:], start):
                if ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        candidate = src[start:i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break

        # Try wrapped in code block: ```json … ```
        cb = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', src, re.DOTALL)
        if cb:
            try:
                return json.loads(cb.group(1))
            except json.JSONDecodeError:
                pass

        # Try a bare JSON object that IS a list item (dict)
        for match in re.finditer(r'\{', src):
            start = match.start()
            depth = 0
            for i, ch in enumerate(src[start:], start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = src[start:i + 1]
                        try:
                            obj = json.loads(candidate)
                            if isinstance(obj, dict):
                                return [obj]
                        except json.JSONDecodeError:
                            break

    return None


# ── Validation ─────────────────────────────────────────────
VALID_TYPES = {
    "Disease", "Symptom", "Treatment", "Medication",
    "Anatomy", "Provider", "Organization"
}

def _validate_triples(raw_triples: list) -> List[Dict]:
    """Strict quality gate: every triple must have non-empty head/relation/tail."""
    valid = []
    for t in raw_triples:
        if not isinstance(t, dict):
            continue
        head     = str(t.get('head',     '')).strip()
        relation = str(t.get('relation', '')).strip()
        tail     = str(t.get('tail',     '')).strip()
        head_type = str(t.get('head_type', 'Entity')).strip()
        tail_type = str(t.get('tail_type', 'Entity')).strip()

        if len(head) < 2 or len(tail) < 2 or len(relation) < 2:
            continue

        # Normalise types
        if head_type not in VALID_TYPES:
            head_type = 'Entity'
        if tail_type not in VALID_TYPES:
            tail_type = 'Entity'

        valid.append({
            "head":      head,
            "head_type": head_type,
            "relation":  relation,
            "tail":      tail,
            "tail_type": tail_type,
        })
    return valid


# ── Main class ─────────────────────────────────────────────
class KMCKnowledgeGraph:
    def __init__(self):
        logger.info(f"Connecting to Ollama at {OLLAMA_HOST} (GPU 0) …")
        self.client = Client(host=OLLAMA_HOST)

        # Warm-up: ensure model is loaded on GPU 0
        try:
            logger.info(f"Pre-loading model {OLLAMA_MODEL} on GPU 0 …")
            self.client.generate(
                model=OLLAMA_MODEL,
                prompt="Hello",
                options={"num_predict": 1}
            )
            logger.info("Model pre-loaded successfully.")
        except Exception as e:
            logger.warning(f"Model pre-load warning (continuing): {e}")

        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            self.driver.verify_connectivity()
            logger.info("Connected to Neo4j successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

        self.processed_ids = self._load_checkpoints()
        self.lock = threading.RLock()
        
        # Persistent file handles for faster I/O
        self.checkpoint_file = open(CHECKPOINT_PATH, 'a', encoding='utf-8')
        self.output_file = open(OUTPUT_FILE, 'a', encoding='utf-8')
        self.neo4j_ok = True

    # ── Checkpointing ──────────────────────────────────────
    def _load_checkpoints(self) -> set:
        if os.path.exists(CHECKPOINT_PATH):
            with open(CHECKPOINT_PATH, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f if line.strip())
        return set()

    def _save_checkpoint(self, entry_id: str):
        with self.lock:
            self.checkpoint_file.write(f"{entry_id}\n")
            self.checkpoint_file.flush()
            self.processed_ids.add(entry_id)

    def close(self):
        try:
            self.driver.close()
        except:
            pass
        try:
            self.checkpoint_file.close()
            self.output_file.close()
        except:
            pass

    # ── Text cleaning ──────────────────────────────────────
    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    # ── Triple extraction ──────────────────────────────────
    def extract_triples(self, text: str, max_retries: int = 5) -> List[Dict]:
        """
        Extract knowledge-graph triples from Kurdish medical text.

        KEY DESIGN DECISION for Qwen3.6:35b
        ─────────────────────────────────────
        • We do NOT pass format="json" to Ollama.
          Qwen3 uses internal Chain-of-Thought (<think>…</think>) before
          writing the final answer.  Forcing JSON mode suppresses that CoT
          block which drastically hurts extraction quality and often produces
          empty output.
        • Instead we prompt the model to wrap its final JSON in a clear
          delimiter (===JSON_START=== / ===JSON_END===) so our parser can
          find it reliably even inside a long reasoning trace.
        • num_predict is set to 8192 to give the CoT enough room.
        """
        prompt = (
            "You are an elite Kurdish medical linguist and knowledge graph engineer.\n"
            "Your task is to extract high-quality, semantically rich medical triples "
            "from the provided Kurdish text.\n\n"

            "CRITICAL QUALITY REQUIREMENTS:\n"
            "1. LANGUAGE: All medical entities and relationships MUST be in natural, "
            "accurate Kurdish (Sorani/Central Kurdish).\n"
            "2. MEANINGFUL RELATIONS: Use precise medical verbs, never 'has' or 'is'.\n"
            "   Examples:\n"
            "   - 'دەبێتە هۆی'           (causes)\n"
            "   - 'نیشانەیە بۆ'           (is a symptom of)\n"
            "   - 'بەکاردێت بۆ چارەسەری'  (used for treatment of)\n"
            "   - 'کاردەکاتە سەر'         (affects)\n"
            "   - 'بەشێکە لە'            (is part of)\n"
            "3. ENTITY TYPES: head_type and tail_type MUST be ONE of: "
            "[Disease, Symptom, Treatment, Medication, Anatomy, Provider, Organization].\n"
            "4. DATA INTEGRITY: Every triple MUST have a valid head, relation, and tail. "
            "No empty strings.\n"
            "5. COMPLETENESS: Extract ALL meaningful medical facts from the text. "
            "Aim for at least 3-8 triples per passage if the text contains medical info.\n\n"

            f"Kurdish Text:\n{text}\n\n"

            "Think carefully about the medical entities and their relationships.\n"
            "After your reasoning, output YOUR FINAL ANSWER between these exact markers:\n"
            "===JSON_START===\n"
            "[\n"
            "  {\n"
            '    "head": "Entity Name in Kurdish",\n'
            '    "head_type": "English Label",\n'
            '    "relation": "Detailed Kurdish Relationship",\n'
            '    "tail": "Target Entity in Kurdish",\n'
            '    "tail_type": "English Label"\n'
            "  }\n"
            "]\n"
            "===JSON_END===\n\n"
            "If the text contains NO meaningful medical relationships, output:\n"
            "===JSON_START===\n"
            "[]\n"
            "===JSON_END==="
        )

        for attempt in range(max_retries):
            try:
                response = self.client.generate(
                    model=OLLAMA_MODEL,
                    prompt=prompt,
                    # ← NO format="json" — allow full CoT output
                    options=OLLAMA_OPTIONS,
                )

                # Resolve response object
                if isinstance(response, dict):
                    content = response.get('response', '')
                else:
                    content = getattr(response, 'response', '')

                if not content or not content.strip():
                    logger.warning(f"[GPU0] Attempt {attempt+1}: Empty response. Retrying…")
                    time.sleep(1)
                    continue

                logger.debug(f"[GPU0] Raw response length: {len(content)} chars")

                # ── Priority 1: extract between our explicit markers ──
                marker_match = re.search(
                    r'===JSON_START===\s*(.*?)\s*===JSON_END===',
                    content, re.DOTALL
                )
                if marker_match:
                    json_str = marker_match.group(1).strip()
                    try:
                        data = json.loads(json_str)
                        if isinstance(data, list):
                            raw_triples = [i for i in data if isinstance(i, dict)]
                            valid = _validate_triples(raw_triples)
                            if valid:
                                logger.info(f"[GPU0] Attempt {attempt+1}: Extracted {len(valid)} valid triples.")
                                return valid
                            elif not raw_triples:
                                # Model explicitly said no triples
                                logger.info(f"[GPU0] Model found no medical relationships in this text.")
                                return []
                            # else: had triples but all failed validation → retry
                            logger.warning(f"[GPU0] Attempt {attempt+1}: All triples failed validation. Retrying…")
                            continue
                    except json.JSONDecodeError:
                        pass  # Fall through to robust extractor

                # ── Priority 2: robust scan of full response ──
                raw_list = _extract_json_from_text(content)
                if raw_list is not None:
                    if isinstance(raw_list, list):
                        if not raw_list:
                            logger.info(f"[GPU0] Attempt {attempt+1}: Model returned empty list.")
                            return []
                        valid = _validate_triples(raw_list)
                        if valid:
                            logger.info(f"[GPU0] Attempt {attempt+1}: Extracted {len(valid)} valid triples (fallback parser).")
                            return valid
                        logger.warning(f"[GPU0] Attempt {attempt+1}: Fallback triples failed validation. Retrying…")
                        continue

                logger.warning(f"[GPU0] Attempt {attempt+1}: No JSON found in response. Retrying…")
                time.sleep(1)

            except Exception as e:
                logger.warning(f"[GPU0] Attempt {attempt+1} Exception: {e}")
                time.sleep(2)

        logger.error("[GPU0] All retries exhausted. Returning empty list.")
        return []

    # ── Neo4j storage ──────────────────────────────────────
    def store_triples(self, triples: List[Dict]):
        """Store multiple triples in a single Neo4j session for efficiency."""
        if not triples or not self.neo4j_ok:
            return
            
        try:
            with self.driver.session() as session:
                for triple in triples:
                    head     = triple.get('head')
                    h_type   = triple.get('head_type', 'Entity')
                    rel      = triple.get('relation',  'RELATED_TO')
                    tail     = triple.get('tail')
                    t_type   = triple.get('tail_type', 'Entity')

                    if not head or not tail:
                        continue

                    # Neo4j label must be alphanumeric
                    h_label = re.sub(r'[^a-zA-Z0-9]', '', str(h_type)) or "Entity"
                    if h_label[0].isdigit(): h_label = "L_" + h_label

                    t_label = re.sub(r'[^a-zA-Z0-9]', '', str(t_type)) or "Entity"
                    if t_label[0].isdigit(): t_label = "L_" + t_label

                    # Sanitize relation
                    rel_clean = re.sub(r'[^a-zA-Z0-9_]', '_', str(rel)).upper()
                    rel_clean = re.sub(r'_+', '_', rel_clean).strip('_') or "RELATED_TO"
                    if rel_clean[0].isdigit(): rel_clean = "R_" + rel_clean

                    query = (
                        f"MERGE (h:{h_label} {{name: $head}}) "
                        f"MERGE (t:{t_label} {{name: $tail}}) "
                        f"MERGE (h)-[r:{rel_clean}]->(t) "
                    )
                    session.run(query, head=head, tail=tail)
        except Exception as e:
            logger.error(f"[GPU0] Neo4j store error: {e}")
            self.neo4j_ok = False

    # ── Dataset processing ─────────────────────────────────
    def process_entry(self, entry: Dict):
        """Process a single entry from the dataset."""
        entry_id = str(entry.get('id', '')).strip()
        
        with self.lock:
            if not entry_id or entry_id in self.processed_ids:
                return

        raw_text = entry.get('response', '')
        if not raw_text or not raw_text.strip():
            self._save_checkpoint(entry_id)
            return

        cleaned_text = self.clean_text(raw_text)
        triples = self.extract_triples(cleaned_text)

        if triples:
            # ── Persist to JSONL ──
            try:
                record = {"id": entry_id, "triples": triples}
                line = json.dumps(record, ensure_ascii=False) + "\n"
                with self.lock:
                    self.output_file.write(line)
                    self.output_file.flush()
                logger.info(f"[GPU0] ID={entry_id}: Extracted {len(triples)} triples.")
            except Exception as e:
                logger.error(f"[GPU0] Failed to write to {OUTPUT_FILE}: {e}")

            # ── Persist to Neo4j ──
            self.store_triples(triples)

        self._save_checkpoint(entry_id)

    def process_dataset(self):
        logger.info(f"[GPU0] Loading dataset from {DATASET_PATH} …")
        try:
            with open(DATASET_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"[GPU0] Could not load dataset: {e}")
            return

        total   = len(data)
        with self.lock:
            already = len(self.processed_ids)
        
        remaining_data = [e for e in data if str(e.get('id', '')).strip() not in self.processed_ids]
        logger.info(f"[GPU0] {total} total | {already} done | {len(remaining_data)} remaining.")

        if not remaining_data:
            logger.info("[GPU0] No entries to process.")
            return

        # Use ThreadPoolExecutor for concurrent requests
        # max_workers=3 is a safe balance for GPU 35b models to overlap I/O and compute
        MAX_WORKERS = 3
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            list(tqdm(
                executor.map(self.process_entry, remaining_data), 
                total=len(remaining_data), 
                desc="GPU0"
            ))

        logger.info("[GPU0] Pipeline finished successfully.")


if __name__ == "__main__":
    kg = KMCKnowledgeGraph()
    try:
        kg.process_dataset()
    except KeyboardInterrupt:
        logger.info("[GPU0] Process interrupted by user. Progress saved.")
    except Exception as e:
        logger.error(f"[GPU0] Fatal error: {e}")
    finally:
        kg.close()
