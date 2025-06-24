import re
from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from openai import OpenAI
import os
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = OpenAI(api_key=api_key)

# Define the structured output response format
response_format = { "type": "json_object" }

# Helper: extract quoted phrases and remaining query
def parse_query(query: str):
    quoted = re.findall(r'"([^"]+)"', query)
    # unquoted = re.sub(r'"[^"]+"', '', query).strip()
    return quoted



# Helper: get embedding for a query (stub, replace with your embedding model)
def get_query_embedding(query: str) -> List[float]:
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=query
    )
    embedding = np.array(response.data[0].embedding, dtype=np.float32)
    
    # Normalize the query embedding
    embedding = embedding.reshape(1, -1)  # Ensure it's 2D
    faiss.normalize_L2(embedding)
    return embedding

# Main hybrid search function
def hybrid_search(entries: List[Dict[str, Any]], query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    quoted = parse_query(query)
    # 1. Keyword filter (if any quoted text)
    filtered = entries
    for phrase in quoted:
        filtered = [e for e in filtered if phrase.lower() in e.get('text', '').lower()]
    # 2. If no semantic query, return filtered
    if not query.strip():
        return filtered[:top_k]
    # 3. Semantic search on filtered results
    # Prepare embeddings matrix
    embeddings = [e['embedding'] for e in filtered if e.get('embedding')]
    if not embeddings:
        return filtered[:top_k]
    embeddings_np = np.array(embeddings).astype('float32')
    # Get query embedding
    query_emb = get_query_embedding(query)
    query_emb_np = np.array([query_emb]).astype('float32')
    # Build FAISS index
    index = faiss.IndexFlatL2(embeddings_np.shape[1])
    index.add(embeddings_np)
    D, I = index.search(query_emb_np, min(top_k, len(filtered)))
    # Return top_k entries in order
    ranked = [filtered[i] for i in I[0]]
    return ranked 