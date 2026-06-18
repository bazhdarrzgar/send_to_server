import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from pyvis.network import Network
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

VECTOR_FILE = "kurdish_medical_vectors.jsonl"
OUTPUT_HTML = "vector_relationships.html"
SIMILARITY_THRESHOLD = 0.85  # Adjust this to show more/fewer relationships

def load_vectors():
    ids = []
    vectors = []
    logging.info(f"Loading vectors from {VECTOR_FILE}...")
    try:
        with open(VECTOR_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                ids.append(str(data['id']))
                vectors.append(data['vector'])
    except FileNotFoundError:
        logging.error(f"{VECTOR_FILE} not found. Please run vector_generator.py first.")
        return [], []
    return ids, np.array(vectors)

def build_graph():
    ids, vectors = load_vectors()
    if not ids:
        return
        
    logging.info(f"Loaded {len(ids)} vectors. Computing similarities...")
    
    # Compute cosine similarity between all vectors
    similarity_matrix = cosine_similarity(vectors)
    
    # Initialize pyvis network
    logging.info("Building interactive graph...")
    net = Network(height="100vh", width="100%", bgcolor="#222222", font_color="white")
    
    # Add nodes
    for i, node_id in enumerate(ids):
        # We only add nodes if they have at least one connection, to keep it clean.
        # But for now, we'll add all of them, or just the ones that connect.
        pass

    # Find relationships (edges) based on similarity using optimized NumPy operations
    edges = []
    connected_nodes = set()
    
    # Get the upper triangle of the similarity matrix (excluding diagonal)
    row_indices, col_indices = np.triu_indices_from(similarity_matrix, k=1)
    
    # Filter indices where similarity is above threshold
    valid_mask = similarity_matrix[row_indices, col_indices] >= SIMILARITY_THRESHOLD
    valid_rows = row_indices[valid_mask]
    valid_cols = col_indices[valid_mask]
    valid_sims = similarity_matrix[valid_rows, valid_cols]
    
    # Optional safety measure: limit max edges so the browser doesn't crash on massive graphs
    MAX_EDGES = 10000
    if len(valid_sims) > MAX_EDGES:
        logging.warning(f"Found {len(valid_sims)} edges, which might freeze the browser. Limiting to top {MAX_EDGES} strongest edges.")
        # Get indices of top MAX_EDGES similarities
        top_indices = np.argsort(valid_sims)[-MAX_EDGES:]
        valid_rows = valid_rows[top_indices]
        valid_cols = valid_cols[top_indices]
        valid_sims = valid_sims[top_indices]

    for r, c, sim in zip(valid_rows, valid_cols, valid_sims):
        edges.append((int(r), int(c), float(sim)))
        connected_nodes.add(int(r))
        connected_nodes.add(int(c))
                
    logging.info(f"Found {len(edges)} strong relationships (similarity >= {SIMILARITY_THRESHOLD}).")
    
    # Add only connected nodes to keep the graph readable
    for node_idx in connected_nodes:
        net.add_node(node_idx, label=f"Document {ids[node_idx]}", title=f"ID: {ids[node_idx]}")
        
    # Add edges
    for i, j, sim in edges:
        # Weight the edge based on similarity
        weight = (sim - SIMILARITY_THRESHOLD) / (1.0 - SIMILARITY_THRESHOLD) * 5
        net.add_edge(i, j, value=weight, title=f"Similarity: {sim:.2f}")

    # Configure physics for a nice Neo4j-like layout
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=250)
    
    # Save the HTML file
    net.save_graph(OUTPUT_HTML)
    logging.info(f"✅ Graph saved to {OUTPUT_HTML}!")
    logging.info(f"Open {OUTPUT_HTML} in any web browser to view the relationships.")

if __name__ == "__main__":
    build_graph()
