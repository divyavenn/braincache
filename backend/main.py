from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime
import os

app = FastAPI()

# --- Models ---
class Bubble(BaseModel):
    id: Optional[int] = None
    text: str
    link: Optional[HttpUrl] = None
    tags: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    embedding: Optional[List[float]] = None  # For semantic search

# --- In-memory store for demo (replace with Supabase later) ---
bubbles_db: List[Bubble] = []

# --- Endpoints ---
@app.post("/entry", response_model=Bubble)
def create_bubble(bubble: Bubble):
    bubble.id = len(bubbles_db) + 1
    bubbles_db.insert(0, bubble)  # Most recent at top
    return bubble

@app.get("/entries", response_model=List[Bubble])
def search_and_list_bubbles(
    query: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tag: Optional[str] = Query(None),
):
    results = bubbles_db
    # Filter by date range
    if start_date or end_date:
        results = [b for b in results if (
            (not start_date or b.timestamp >= start_date) and
            (not end_date or b.timestamp <= end_date)
        )]
    # Filter by tag
    if tag:
        results = [b for b in results if tag in b.tags]
    # Filter by query (text or tags)
    if query:
        results = [b for b in results if query.lower() in b.text.lower() or any(query.lower() in t.lower() for t in b.tags)]
    return results


from supabase import create_client, Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# TODO: Replace in-memory store with Supabase DB
# TODO: Add authentication using Supabase
# TODO: Implement semantic search using embeddings
