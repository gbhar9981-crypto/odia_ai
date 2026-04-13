from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from dotenv import load_dotenv
import os

from app.db.database import get_db
from app.db.qdrant_client import check_qdrant_health, init_qdrant_collections
from app.api import auth, chat, document, user

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Odia AI API",
    description="Backend API for Odia AI Multilingual Chat & Knowledge Base",
    version="1.0.0"
)

# CORS configuration for Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Odia AI Backend API"}

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    health_status = {
        "status": "healthy",
        "services": {
            "database": "unknown",
            "qdrant": "unknown",
            "gemini_api": "searching"
        }
    }
    
    # 1. Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "connected"
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        
    
    # 2. Check Qdrant
    if check_qdrant_health():
        health_status["services"]["qdrant"] = "connected"
    else:
        health_status["services"]["qdrant"] = "error: unreachable"
        health_status["status"] = "degraded"
        
        health_status["status"] = "degraded"
        
    # 4. Check Gemini Key
    key = os.getenv("GEMINI_API_KEY")
    if key and key != "your_gemini_api_key_here":
        health_status["services"]["gemini_api"] = "configured"
    else:
        health_status["services"]["gemini_api"] = "missing placeholder"
        health_status["status"] = "degraded"
        
    return health_status

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(document.router, prefix="/api/document", tags=["documents"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
