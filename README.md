# Braincache

A simple web app for capturing and searching knowledge bubbles.

## Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React + TypeScript (Vite)
- **Auth & DB:** Supabase

---

## Project Structure

```
braincache/
├── backend/         # FastAPI app
│   ├── main.py
│   ├── requirements.txt
│   └── ...
├── frontend/        # React + TypeScript app (Vite)
│   ├── src/
│   ├── package.json
│   └── ...
└── README.md
```

---

## Getting Started

### 1. Backend (FastAPI)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### 2. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

### 3. Supabase
- Set up a Supabase project at [supabase.com](https://supabase.com/)
- Create a `.env` file in `backend/` and `frontend/` with your Supabase credentials (see Supabase docs)

---

## Features
- List of text bubbles (text, optional link, tags, timestamp)
- Input bubble at the top for new entries
- Command-K to paste a link
- Hashtag parsing for tags
- Semantic search (search icon)
- Date picker for filtering

---

## Next Steps
- Implement backend endpoints in `backend/main.py`
- Connect frontend to Supabase and backend
- Add authentication and database logic
