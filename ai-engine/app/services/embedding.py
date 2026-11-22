import asyncio
import hashlib
import json
from typing import List

from langchain_ollama import OllamaEmbeddings

from app.core.config import settings

CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


class EmbeddingService:
    def __init__(self, model_name: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        """
        Initializes the local embedding service using LangChain and Ollama.
        """
        self.model_name = model_name
        self.embeddings = OllamaEmbeddings(
            model=model_name,
            base_url=base_url
        )

    def embed_text(self, text: str) -> List[float]:
        """
        Generates a vector embedding for a single text query or document chunk.
        (Synchronous and uncached. Blocks the event loop if called from async code.)
        """
        return self.embeddings.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generates vector embeddings for a batch of document chunks.
        """
        return self.embeddings.embed_documents(texts)

    def _cache_key(self, text: str) -> str:
        # The model name is part of the key: a different model must never reuse old vectors.
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"emb:{self.model_name}:{digest}"

    async def embed_query_cached(self, text: str, redis) -> List[float]:
        """
        Async, Redis-cached embedding for a single query.

        - Cache hit: returns the stored vector, Ollama is not called.
        - Cache miss: embeds in a worker thread (does not block the event loop),
          stores the vector for 24 hours, returns it.
        - Redis down or broken: falls back to embedding directly. Never raises because of Redis.
        `redis` is the client from request.app.state.redis.
        """
        key = self._cache_key(text)

        try:
            cached = await redis.get(key)
            if cached:
                print("[embedding-cache] HIT")
                return json.loads(cached)
        except Exception:
            pass  # cache is best effort

        print("[embedding-cache] MISS")
        vector = await asyncio.to_thread(self.embeddings.embed_query, text)

        try:
            await redis.set(key, json.dumps(vector), ex=CACHE_TTL_SECONDS)
        except Exception:
            pass

        return vector


# Singleton instance for easy import across endpoints and services
embedding_service = EmbeddingService(
    model_name=settings.EMBEDDING_MODEL_NAME,
    base_url=settings.OLLAMA_BASE_URL
)