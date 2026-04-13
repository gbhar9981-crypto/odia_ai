from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import os
import shutil

from app.db.database import get_db
from app.models.models import Document, User
from app.services.vector_service import vector_service
from app.api.deps import get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Configuration for subscription-based limits
LIMITS = {
    "free": {"max_files": 15, "max_size_mb": 45},
    "premium": {"max_files": 50, "max_size_mb": 155}
}

import fitz # PyMuPDF
import logging

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """
    Uploads a document, extracts text via PyMuPDF, and pushes chunks to Qdrant.
    """
    user_tier = "premium" if current_user.is_premium else "free"
    max_files = LIMITS[user_tier]["max_files"]
    max_size = LIMITS[user_tier]["max_size_mb"] * 1024 * 1024
    
    # 1. Check current file count
    result = await db.execute(select(Document).where(Document.owner_id == current_user.id))
    existing_docs = result.scalars().all()
    if len(existing_docs) >= max_files:
        raise HTTPException(status_code=400, detail=f"Upload limit reached. You can only have {max_files} files.")
        
    # 2. Check file size
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail=f"File too large. Max is {LIMITS[user_tier]['max_size_mb']}MB.")
    
    # 3. Save physical file
    file_path = os.path.join(UPLOAD_DIR, f"{current_user.id}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(content)
        
    # 4. Save to Database as PROCESSING
    new_doc = Document(
        filename=file.filename,
        filepath=file_path,
        file_size_mb=len(content) / (1024 * 1024),
        owner_id=current_user.id,
        upload_status="PROCESSING"
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    
    # 5. Extract text and Index for RAG
    try:
        chunks = []
        if file.filename.lower().endswith(".pdf"):
            doc = fitz.open(file_path)
            for page in doc:
                text = page.get_text("text").strip()
                if text:
                    # Very simple chunking: split by paragraphs
                    paragraphs = text.split("\n\n")
                    for p in paragraphs:
                        if len(p.strip()) > 30: # Ignore tiny sentences
                            chunks.append(p.strip())
            doc.close()
        else:
            # Fallback for txt/md files
            text = content.decode('utf-8', errors='ignore')
            chunks = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]

        if not chunks:
            chunks = ["No extractable text found in this document."]

        # Send to Vector DB
        res = await vector_service.add_document_chunks(chunks, new_doc.id)
        if res is None:
            raise ValueError("Vector DB Upsert returned None (usually network/timeout error).")

        new_doc.upload_status = "READY"
        await db.commit()

    except Exception as e:
        logging.error(f"Error indexing document {new_doc.id}: {e}")
        new_doc.upload_status = "ERROR"
        await db.commit()
        # We don't raise 500 here because the file IS saved. The user will see 'ERROR' in UI.

    return {"message": "File processed.", "document_id": new_doc.id, "status": new_doc.upload_status}

@router.get("/list")
async def list_documents(
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """
    Returns only the documents owned by the currently logged-in user.
    """
    result = await db.execute(select(Document).where(Document.owner_id == current_user.id))
    docs = result.scalars().all()
    return {"documents": [{"id": d.id, "name": d.filename, "size": d.file_size_mb, "status": d.upload_status} for d in docs]}

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes a document after verifying ownership.
    """
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.owner_id == current_user.id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied")
        
    # Physical delete
    if os.path.exists(doc.filepath):
        os.remove(doc.filepath)
        
    # DB and Vector delete
    await db.delete(doc)
    await db.commit()
    return {"message": "Document deleted successfully"}
