import os
import json
from autollm import AutoQueryEngine
from llama_index.core import Document, Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding

# Configuration
DATASET_PATH = "kurdish_medical_corpus_kmc.json"
MODEL_NAME = "gemma4:27b"  # User specified model
OLLAMA_BASE_URL = "http://localhost:11434"

def load_kurdish_medical_dataset(path):
    """
    Loads the Kurdish Medical Corpus (KMC) from JSON.
    Handles the comment block at the beginning of the file.
    """
    print(f"Loading dataset: {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
        # The file starts with a C-style comment block /* ... */
        # We find the first '[' to start parsing the JSON array
        json_start = content.find("[")
        if json_start != -1:
            data = json.loads(content[json_start:])
        else:
            data = json.loads(content)
            
    print(f"Successfully loaded {len(data)} instruction-response pairs.")
    return data

def main():
    # 1. Load the dataset
    data = load_kurdish_medical_dataset(DATASET_PATH)

    # 2. Convert to LlamaIndex Documents for indexing
    # We combine instruction and response to provide full context for retrieval
    documents = []
    for entry in data:
        text = f"پسیار (Question): {entry.get('instruction')}\nوەڵام (Answer): {entry.get('response')}"
        doc = Document(
            text=text,
            metadata={
                "id": entry.get("id"),
                "title": entry.get("document", {}).get("title", ""),
                "domain": entry.get("document", {}).get("domain", ""),
                "source": entry.get("document", {}).get("source_url", "")
            }
        )
        documents.append(doc)

    # 3. Setup Ollama Framework
    # Note: Ensure you have run 'ollama pull gemma4:27b' first.
    print(f"Setting up Ollama with model: {MODEL_NAME}")
    llm = Ollama(model=MODEL_NAME, base_url=OLLAMA_BASE_URL, request_timeout=600.0)
    
    # Local embedding model via Ollama
    # Note: You can use a smaller model for faster embeddings if needed (e.g. 'nomic-embed-text')
    embed_model = OllamaEmbedding(model_name=MODEL_NAME, base_url=OLLAMA_BASE_URL)

    # Configure global settings for autollm/llama-index
    Settings.llm = llm
    Settings.embed_model = embed_model

    # 4. Configuration of AutoQueryEngine (Modified from Quickstart)
    system_prompt = (
        "تۆ یاریدەدەرێکی پزیشکی کوردی (سۆرانی). "
        "بەکارهێنانی بەڵگەنامە پزیشکییە دابینکراوەکان بۆ وەڵامدانەوەی پرسیارەکان بە وردی. "
        "You are a Kurdish Medical AI Assistant. Answer questions based on the provided documents."
    )
    
    query_wrapper_prompt = (
        "Zanyariyakan lera dabin krawn:\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Pêyî em zanyariyaney serewe, weļamî em pirsyare biderewe:\n"
        "Pirsyar: {query_str}\n"
        "Weļam:\n"
    )

    print("Initializing AutoQueryEngine with LanceDB (RAG Mode)...")
    query_engine = AutoQueryEngine.from_defaults(
        documents=documents,
        llm=llm,
        embed_model=embed_model,
        vector_store_type="LanceDBVectorStore",
        lancedb_uri="./.lancedb",
        system_prompt=system_prompt,
        query_wrapper_prompt=query_wrapper_prompt,
        # Additional params from notebook
        chunk_size=512,
        chunk_overlap=48,
        similarity_top_k=3
    )

    print("\nInitialization Complete.")
    print("The Kurdish Medical AI is ready to respond.")
    
    # Interactive Query Loop
    print("\nAsk a medical question (type 'exit' to quit):")
    while True:
        user_input = input("\nQuery: ")
        if user_input.lower() in ["exit", "quit", "کۆتایی"]:
            break
            
        if not user_input.strip():
            continue

        try:
            print("Thinking...")
            response = query_engine.query(user_input)
            print("\n--- وەڵام (Answer) ---")
            print(response.response)
            print("----------------------")
        except Exception as e:
            print(f"Error processing query: {e}")

if __name__ == "__main__":
    main()
