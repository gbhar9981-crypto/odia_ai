import os
import fitz # PyMuPDF
from PIL import Image

def manual_text_splitter(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> list[str]:
    """
    Manual recursive-style splitter that doesn't require LangChain.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
    return chunks

def extract_text_from_file(filepath: str, filename: str) -> str:
    """
    Extracts text from PDF, Text, or supported Image files.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    text = ""
    if ext == ".pdf":
        try:
            doc = fitz.open(filepath)
            for page in doc:
                text += page.get_text("text") + "\n"
        except Exception as e:
            print(f"Error reading PDF: {e}")
    elif ext in [".txt", ".md", ".csv"]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        except:
            pass
    elif ext in [".png", ".jpg", ".jpeg"]:
        # In a real app, you would use Gemini Vision or Tesseract OCR here
        text = f"Image file detected: {filename}. Visual content cannot be text-parsed without Vision model."
    
    return text

def chunk_document_text(text: str) -> list[str]:
    """
    Splits the document text into manageable chunks for embeddings.
    Using native Python manual_text_splitter to avoid gRPC-blocked SDKs.
    """
    return manual_text_splitter(text, chunk_size=1000, chunk_overlap=150)
