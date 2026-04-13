import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_BASE_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

def init_qdrant_collections():
    """
    Initializes the required Qdrant collections for document indexing via REST.
    """
    collection_name = "document_chunks"
    
    with httpx.Client() as client:
        try:
            # Check if collection exists
            response = client.get(f"{QDRANT_BASE_URL}/collections")
            response.raise_for_status()
            collections = response.json().get("result", {}).get("collections", [])
            
            if not any(col.get("name") == collection_name for col in collections):
                # Create collection via REST PUT
                print(f"Creating collection '{collection_name}' via REST...")
                create_payload = {
                    "vectors": {
                        "size": 768, # Google Gemini Embedding size
                        "distance": "Cosine"
                    }
                }
                create_res = client.put(f"{QDRANT_BASE_URL}/collections/{collection_name}", json=create_payload)
                create_res.raise_for_status()
                print(f"Collection '{collection_name}' created successfully.")
            else:
                print(f"Collection '{collection_name}' already exists.")
        except Exception as e:
            print(f"Warning: Failed to connect to Qdrant REST - {str(e)}")

def check_qdrant_health() -> bool:
    """
    Checks if Qdrant REST is reachable.
    """
    try:
        with httpx.Client() as client:
            response = client.get(f"{QDRANT_BASE_URL}/collections", timeout=2.0)
            return response.status_code == 200
    except:
        return False
