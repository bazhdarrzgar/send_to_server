import json
import os
import logging
from typing import List, Dict
from tqdm import tqdm
import torch
from transformers import AutoTokenizer, AutoModel

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vector_pipeline.log"),
        logging.StreamHandler()
    ]
)

# Configuration
# We use bert-large-cased as requested for BERT
MODEL_NAME = "bert-large-cased"
DATASET_PATH = "../just_data_vector/kurdish_medical_corpus_kmc.json"
OUTPUT_PATH = "kurdish_medical_vectors.jsonl"
CHECKPOINT_PATH = "processed_ids.txt"

class VectorGenerator:
    def __init__(self):
        logging.info(f"Downloading/Loading Model: {MODEL_NAME}")
        # Initialize tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModel.from_pretrained(MODEL_NAME)
        
        # Check if GPU is available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        logging.info(f"Model loaded and moved to {self.device}")
        
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

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        # Basic cleanup
        text = text.replace('\n', ' ')
        text = ' '.join(text.split())
        return text

    def generate_vectors_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates vector embeddings for a batch of texts using XLM-R.
        """
        if not texts:
            return []
            
        try:
            # Tokenize input text in batches
            inputs = self.tokenizer(
                texts,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)
            
            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                
            # Mean pooling of the last hidden states
            attention_mask = inputs['attention_mask'].unsqueeze(-1).expand(outputs.last_hidden_state.size()).float()
            sum_embeddings = torch.sum(outputs.last_hidden_state * attention_mask, 1)
            sum_mask = torch.clamp(attention_mask.sum(1), min=1e-9)
            mean_pooled = sum_embeddings / sum_mask
            
            # Convert to list of lists of floats
            vectors = mean_pooled.cpu().numpy().tolist()
            return vectors
            
        except Exception as e:
            logging.warning(f"Vector generation failed for batch... Error: {e}")
            return [[] for _ in texts]

    def store_vectors_batch(self, entry_ids: List[str], vectors: List[List[float]]):
        """
        Appends a batch of generated vectors to the JSONL file.
        """
        with open(OUTPUT_PATH, 'a', encoding='utf-8') as f:
            for entry_id, vector in zip(entry_ids, vectors):
                if not vector:
                    continue
                record = {
                    "id": entry_id,
                    "vector": vector
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def process_dataset(self, batch_size: int = 32):
        logging.info(f"Loading dataset from {DATASET_PATH}...")
        try:
            with open(DATASET_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logging.error(f"Could not load JSON: {e}")
            return

        logging.info(f"Processing {len(data)} entries with batch_size={batch_size}. Found {len(self.processed_ids)} already processed.")
        
        batch_ids = []
        batch_texts = []
        
        for entry in tqdm(data):
            entry_id = entry.get('id')
            if not entry_id or entry_id in self.processed_ids:
                continue
                
            raw_text = entry.get('response', '')
            if not raw_text:
                self._save_checkpoint(entry_id)
                continue
                
            cleaned_text = self.clean_text(raw_text)
            
            batch_ids.append(entry_id)
            batch_texts.append(cleaned_text)
            
            if len(batch_ids) >= batch_size:
                vectors = self.generate_vectors_batch(batch_texts)
                self.store_vectors_batch(batch_ids, vectors)
                
                # Save checkpoints
                for b_id in batch_ids:
                    self._save_checkpoint(b_id)
                    
                batch_ids = []
                batch_texts = []
                
        # Process remaining
        if batch_ids:
            vectors = self.generate_vectors_batch(batch_texts)
            self.store_vectors_batch(batch_ids, vectors)
            for b_id in batch_ids:
                self._save_checkpoint(b_id)
            
        logging.info("Pipeline finished successfully.")

if __name__ == "__main__":
    generator = VectorGenerator()
    try:
        generator.process_dataset()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user. Progress saved.")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
