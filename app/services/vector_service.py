import os
import httpx
import uuid
import json
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_BASE_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

class VectorService:
    def __init__(self, collection_name="document_chunks_v2"):
        self.collection_name = collection_name
        self.embed_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={GEMINI_API_KEY}"

    async def initialize_collection(self):
        """Ensures the Qdrant collection exists before using it."""
        async with httpx.AsyncClient() as client:
            try:
                # Check if exists
                res = await client.get(f"{QDRANT_BASE_URL}/collections/{self.collection_name}")
                if res.status_code == 404:
                    print(f"Collection {self.collection_name} not found. Creating it...")
                    # gemini-embedding-001 is 3072 dimensions
                    payload = {
                        "vectors": {
                            "size": 3072,
                            "distance": "Cosine"
                        }
                    }
                    await client.put(f"{QDRANT_BASE_URL}/collections/{self.collection_name}", json=payload)
                    print("Collection created successfully.")
            except Exception as e:
                print(f"Failed to initialize Qdrant collection: {e}")

    async def get_embeddings(self, text: str) -> list[float]:
        """
        Generates Gemini embeddings for a given text snippet via REST.
        """
        if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
            raise ValueError("Gemini API Key missing.")

        payload = {
            "model": "models/gemini-embedding-001",
            "content": {
                "parts": [{"text": text}]
            }
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.embed_url, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", {}).get("values", [])
            except Exception as e:
                print(f"Embedding Retrieval Error: {str(e)}")
                return []

    async def upsert_points(self, points: list[dict]):
        """
        Upserts vector points into Qdrant via REST.
        """
        async with httpx.AsyncClient() as client:
            try:
                payload = {"points": points}
                response = await client.put(f"{QDRANT_BASE_URL}/collections/{self.collection_name}/points", json=payload)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Qdrant Upsert Error: {str(e)}")
                return None

    async def add_document_chunks(self, chunks: list[str], document_id: int):
        """
        Processes document chunks, generates embeddings, and indexes them in Qdrant via REST.
        """
        await self.initialize_collection()
        points = []
        for i, chunk in enumerate(chunks):
            vector = await self.get_embeddings(chunk)
            if vector:
                # Create a point object for Qdrant REST
                point_id = str(uuid.uuid4())
                points.append({
                    "id": point_id,
                    "vector": vector,
                    "payload": {
                        "text": chunk,
                        "document_id": document_id,
                        "chunk_index": i
                    }
                })
        
        if points:
            return await self.upsert_points(points)
        return None

    async def query_similar_chunks(self, query: str, document_id: int = None, limit: int = 4) -> str:
        """
        Queries the vector store for the most relevant context via REST.
        """
        query_vector = await self.get_embeddings(query)
        if not query_vector:
            return ""

        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "vector": query_vector,
                    "limit": limit,
                    "with_payload": True
                }
                
                if document_id is not None:
                    payload["filter"] = {
                        "must": [
                            {
                                "key": "document_id",
                                "match": {"value": document_id}
                            }
                        ]
                    }

                response = await client.post(f"{QDRANT_BASE_URL}/collections/{self.collection_name}/points/search", json=payload)
                response.raise_for_status()
                results = response.json().get("result", [])
                
                context_parts = [res["payload"]["text"] for res in results if "payload" in res]
                return "\n---\n".join(context_parts)
            except Exception as e:
                print(f"Qdrant Search Error: {str(e)}")
                return ""

# Singleton instance
vector_service = VectorService()
