import os
from langchain_community.graphs import Neo4jGraph
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain.chains import GraphCypherQAChain
from langchain_community.vectorstores import Neo4jVector
from dotenv import load_dotenv

# Load configurations
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:26b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

# Initialize models
llm = OllamaLLM(model=OLLAMA_MODEL)
embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

# Initialize Neo4j Graph
graph = Neo4jGraph(url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD)

# 1. Setup Graph Cypher Chain (for structured queries)
cypher_chain = GraphCypherQAChain.from_llm(
    llm, 
    graph=graph, 
    verbose=True,
    allow_dangerous_requests=True # Required for Cypher generation
)

# 2. Setup Vector Store (for semantic search)
vector_index = Neo4jVector.from_existing_graph(
    embeddings,
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD,
    index_name="medical_index",
    node_label="Response",
    text_node_properties=["text"],
    embedding_node_property="embedding",
)

def hybrid_query(question):
    """
    Combines Graph search and Vector search to answer medical questions.
    """
    print(f"\n--- وەڵامی پرسیار: {question} ---\n")
    
    # Step 1: Semantic Search via Vector Index
    print("Searching vector index...")
    docs = vector_index.similarity_search(question, k=3)
    vector_context = "\n".join([doc.page_content for doc in docs])
    
    # Step 2: Graph Search via Cypher
    print("Searching knowledge graph...")
    graph_context = ""
    try:
        graph_context = cypher_chain.invoke({"query": question})["result"]
    except Exception as e:
        print(f"Graph search error: {e}")
        graph_context = "زانیاری لە گرافەکەدا نەدۆزرایەوە."

    # Step 3: Final Synthesis with Thinking
    prompt = f"""
    تۆ یاریدەدەرێکی پزیشکی پسپۆڕی کوردیییت (Central Kurdish).
    
    بۆ ئەوەی باشترین وەڵام بدەیتەوە، سەرەتا لە دڵی خۆتدا بیر بکەرەوە (Think step-by-step):
    1. پێداچوونەوە بە زانیارییەکانی گەڕانی ڤێکتەری (Vector Search).
    2. پێداچوونەوە بە زانیارییەکانی گەڕانی گراف (Graph Search).
    3. بەراوردکردنی زانیارییەکان و دڵنیابوونەوە لە ڕاستی پزیشکی.
    
    پاشان وەڵامێکی گشتگیر و ڕوون بە زمانی کوردی (سۆرانی) بنووسە.
    
    Context from Vector Search:
    {vector_context}
    
    Context from Graph Search:
    {graph_context}
    
    Question: {question}
    
    وەڵامەکەت بەم شێوەیە دابەش بکە:
    <thinking>
    (لێرەدا هەنگاوەکانی بیرکردنەوەت بنووسە بە کوردی)
    </thinking>
    
    وەڵامی کۆتایی:
    (لێرەدا وەڵامی کۆتایی بۆ بەکارهێنەر بنووسە)
    """
    
    response = llm.invoke(prompt)
    return response

if __name__ == "__main__":
    # Example queries
    test_questions = [
        "نیشانەکانی ئەنفلۆنزا چیین؟",
        "چارەسەری بەرزبوونەوەی پلەی گەرمی چییە؟",
        "ڕۆڵی پەرستاران لە نەخۆشخانەدا چییە؟"
    ]
    
    for q in test_questions:
        ans = hybrid_query(q)
        print(f"\nResponse:\n{ans}\n")
        print("-" * 50)
