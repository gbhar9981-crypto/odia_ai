from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import json
import asyncio

from app.db.database import get_db
from app.models.models import User, ChatMessage, Document, ChatThread
from app.services.llm_service import llm_service
from app.services.vector_service import vector_service
from app.api.deps import get_current_user

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    document_id: int | None = None
    thread_id: int | None = None

class TranslateRequest(BaseModel):
    text: str

@router.post("/stream")
async def stream_chat(
    request: ChatRequest, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """
    Standard chat endpoint. Performs RAG if document_id is present.
    Creates a new thread if thread_id is not provided.
    Saves both user and AI messages to the database for the verified current user.
    """
    # 1. Manage Thread
    thread_id = request.thread_id
    if not thread_id:
        new_thread = ChatThread(user_id=current_user.id, title=request.message[:30] + "...")
        db.add(new_thread)
        await db.commit()
        await db.refresh(new_thread)
        thread_id = new_thread.id
    else:
        # Verify ownership
        thread_result = await db.execute(select(ChatThread).where(ChatThread.id == thread_id, ChatThread.user_id == current_user.id))
        if not thread_result.scalars().first():
            raise HTTPException(status_code=403, detail="Not authorized to access this thread")
    
    # 2. Save User Message
    user_msg = ChatMessage(thread_id=thread_id, role="user", content=request.message)
    db.add(user_msg)
    await db.commit()

    # 3. Context & AI Generation
    context = ""
    if request.document_id:
        # Verify document ownership
        doc_result = await db.execute(select(Document).where(Document.id == request.document_id, Document.owner_id == current_user.id))
        if doc_result.scalars().first():
            context = await vector_service.query_similar_chunks(request.message, document_id=request.document_id, limit=4)
        else:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")
    
    response_text = await llm_service.generate_response(request.message, context=context)
    
    # 4. Save AI Response
    ai_msg = ChatMessage(thread_id=thread_id, role="ai", content=response_text)
    db.add(ai_msg)
    await db.commit()

    async def event_generator():
        yield f"data: THREAD_ID:{thread_id}\n\n"
        
        # Split but keep the space by appending it to each word
        words = response_text.split()
        for i, word in enumerate(words):
            # Add a space after every word except potentially the last (or just add it anyway)
            suffix = " " if i < len(words) - 1 else ""
            yield f"data: {word}{suffix}\n\n"
            await asyncio.sleep(0.04)
        yield "data: [DONE]\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/threads")
async def get_all_threads(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Returns only the threads belonging to the current user.
    """
    result = await db.execute(
        select(ChatThread).where(ChatThread.user_id == current_user.id).order_by(ChatThread.created_at.desc())
    )
    threads = result.scalars().all()
    return {"threads": [{"id": t.id, "title": t.title, "date": t.created_at.strftime("%Y-%m-%d")} for t in threads]}

@router.get("/history/{thread_id}")
async def get_chat_history(
    thread_id: int, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the chat history of a specific thread, after verifying ownership.
    """
    thread_result = await db.execute(select(ChatThread).where(ChatThread.id == thread_id, ChatThread.user_id == current_user.id))
    if not thread_result.scalars().first():
        raise HTTPException(status_code=403, detail="Access denied")
        
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.thread_id == thread_id).order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return {
        "messages": [{"id": m.id, "sender": m.role.upper(), "message": m.content} for m in messages]
    }

@router.post("/translate")
async def translate_odia_to_english(request: TranslateRequest):
    translation = await llm_service.generate_translation(request.text)
    return {"translation": translation}
