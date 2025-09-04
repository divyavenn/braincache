from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Dict, Any
from jose import jwt
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
if not SUPABASE_JWT_SECRET:
    raise ValueError("SUPABASE_JWT_SECRET environment variable is not set")

# Convert to bytes if needed
if isinstance(SUPABASE_JWT_SECRET, str):
    SUPABASE_JWT_SECRET = SUPABASE_JWT_SECRET.encode('utf-8')

# Use HTTPBearer for JWT tokens
security = HTTPBearer()

test_token = "eyJhbGciOiJIUzI1NiIsImtpZCI6IndycWR6dmdEdjNHcERNMzUiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2pqc3dhZm9wZmV1a3VpZmRvdGhqLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI1YTI3M2M0ZS1lNDg3LTQ3ZjEtYWUyZC1lMDZlZTYxY2M1YTgiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzUwODU4Njc2LCJpYXQiOjE3NTA4NTUwNzYsImVtYWlsIjoidmVubi5kaXZ5YUBnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoidmVubi5kaXZ5YUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwicGhvbmVfdmVyaWZpZWQiOmZhbHNlLCJzdWIiOiI1YTI3M2M0ZS1lNDg3LTQ3ZjEtYWUyZC1lMDZlZTYxY2M1YTgifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc1MDg1NTA3Nn1dLCJzZXNzaW9uX2lkIjoiMjcyNDc4YTgtNzUyMy00ODBiLTk0NGEtODRiOWVlNTlkZDc0IiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.PD4L8WrdA3nkRrHUyq7KTWJDUyUh4Slyelx83Zk9nYg"

def get_current_user(credentials = Depends(security)) -> Dict[str, Any]:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {"user_id": user_id, "email": email}
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
