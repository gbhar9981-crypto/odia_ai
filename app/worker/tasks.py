import os
import asyncio
from app.services.document_parser import extract_text_from_file, chunk_document_text
from app.services.vector_service import vector_service

async def process_document_task(document_id: int, filepath: str, filename: str, user_id: int):
    """
    Background worker task to extract text from a file, generating embeddings 
    and inserting them into Qdrant via REST.
    This version is async and designed for FastAPI BackgroundTasks.
    """
    print(f"Starting pipeline for document {document_id}: {filename}")
    
    # 1. Extract text
    text = extract_text_from_file(filepath, filename)
    if not text.strip():
        print(f"Warning: No text extracted from {filename}")
        return
        
    # 2. Chunk text
    chunks = chunk_document_text(text)
    print(f"Extracted {len(chunks)} chunks from {filename}.")
    
    # 3. Embed and save to Qdrant (via REST)
    await vector_service.add_document_chunks(chunks, document_id)
    
    # 4. Cleanup/Completion status (in a full system, you would update the Postgres status to 'READY')
    print(f"Completed processing for document {document_id}.")
