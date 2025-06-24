from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
import os
from dotenv import load_dotenv
from supabase import create_client, Client

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
    embedding: Optional[List[float]] = None
    tags: List[str] = Field(default_factory=list)
    assets: Optional[Any] = None  # List or dict, depending on your usage

# --- Endpoints ---
@app.post("/entry", response_model=Entry)
def create_entry(entry: Entry):
    data = entry.dict(exclude_unset=True)
    # Supabase expects tags and assets as JSON
    if "tags" in data and not isinstance(data["tags"], list):
        data["tags"] = [data["tags"]]
    if "assets" in data and data["assets"] is None:
        data["assets"] = []
    response = supabase.table("entries").insert(data).execute()
    if response.error:
        raise HTTPException(status_code=500, detail=response.error.message)
    created = response.data[0]
    return Entry(**created)

@app.get("/entries", response_model=List[Entry])
def search_and_list_entries(
    query: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    tag: Optional[str] = Query(None),
):
    q = supabase.table("entries")
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
    return [Entry(**item) for item in response.data]

# TODO: Replace in-memory store with Supabase DB
# TODO: Add authentication using Supabase
# TODO: Implement semantic search using embeddings
