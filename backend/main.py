from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from search import hybrid_search  # Import the hybrid search function
from auth import get_current_user

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# --- Models ---
class Entry(BaseModel):
    id: Optional[int] = None
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    text: str
    tags: List[str] = Field(default_factory=list)
    assets: Optional[Any] = None  # List or dict, depending on your usage
    embedding: Optional[List[float]] = None  # Now matches float8[] in Supabase

# --- Endpoints ---
@app.post("/entry", response_model=Entry)
def create_entry(entry: Entry, user_id: str = Depends(get_current_user)):
    data = entry.dict(exclude_unset=True)
    data["user_id"] = user_id
    # Supabase expects tags and assets as JSON
    if "tags" in data and not isinstance(data["tags"], list):
        data["tags"] = [data["tags"]]
    if "assets" in data and data["assets"] is None:
        data["assets"] = []
    if "embedding" in data and data["embedding"] is None:
        data["embedding"] = []
    response = supabase.table("entries").insert(data).execute()
    if response.error:
        raise HTTPException(status_code=500, detail=response.error.message)
    created = response.data[0]
    return Entry(**created)


{
  "id": 0,
  "user_id": "5a273c4e-e487-47f1-ae2d-e06ee61cc5a8",
  "created_at": "2025-06-24T07:19:48.479Z",
  "text": "hi i'm trying this out",
  "tags": ["test"],
  "assets": [],
  "embedding": [0]
}

@app.get("/entries", response_model=List[Entry])
def search_and_list_entries(
    query: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tag: Optional[str] = Query(None),
    top_k: int = 10,
    user_id: str = Depends(get_current_user)
):
    q = supabase.table("entries").eq("user_id", user_id)
    # Date range filter
    if start_date:
        q = q.gte("created_at", start_date.isoformat())
    if end_date:
        q = q.lte("created_at", end_date.isoformat())
    # Tag filter
    if tag:
        q = q.contains("tags", [tag])
    # Text query filter (simple, not semantic)
    if query:
        q = q.ilike("text", f"%{query}%")
    q = q.order("created_at", desc=True)
    response = q.execute()
    if response.error:
        raise HTTPException(status_code=500, detail=response.error.message)
    entries = response.data
    # If query is provided, use hybrid search
    if query:
        try:
            results = hybrid_search(entries, query, top_k=top_k)
        except NotImplementedError as e:
            raise HTTPException(status_code=501, detail=str(e))
        return results
    # Otherwise, return the most recent entries
    return [Entry(**item) for item in entries[:top_k]]

# TODO: Replace in-memory store with Supabase DB
# TODO: Add authentication using Supabase
# TODO: Implement semantic search using embeddings
