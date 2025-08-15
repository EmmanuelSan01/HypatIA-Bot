# Si se requiere recuperar contexto desde la base vectorial antes de enviar al LLM

import os
import logging
from typing import List, Dict, Any, Optional

import anyio
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, SearchRequest, PointStruct

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "company_kb")
QDRANT_ENABLED = os.getenv("QDRANT_ENABLED", "true").lower() == "true"

# Embeddings: puedes cambiar por OpenAI con una flag (ver requisitos). :contentReference[oaicite:2]{index=2}
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")

_client: Optional[QdrantClient] = None

def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return _client

async def embed_text(text: str) -> List[float]:
    """
    Coloca aquí tu implementación real de embeddings (FastEmbed u OpenAI).
    Para MVP, retornamos un vector dummy para no romper el flujo si aún no conectas embeddings.
    """
    # TODO: integrar FastEmbed/SentenceTransformers/OpenAI según config
    return [0.0] * 384  # tamaño sugerido en requisitos con FastEmbed. :contentReference[oaicite:3]{index=3}

async def retrieve_context(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    if not QDRANT_ENABLED:
        return []

    vec = await embed_text(query)

    def _search():
        client = get_client()
        res = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=vec,
            limit=top_k,
            with_payload=True,
        )
        return res

    try:
        results = await anyio.to_thread.run_sync(_search)
        docs = []
        for r in results:
            payload = r.payload or {}
            docs.append(
                {
                    "text": payload.get("text", ""),
                    "title": payload.get("title", ""),
                    "source": payload.get("source", ""),
                    "score": getattr(r, "score", None),
                }
            )
        return docs
    except Exception as e:
        logger.exception("qdrant.retrieve_context.error", extra={"error": str(e)})
        return []
