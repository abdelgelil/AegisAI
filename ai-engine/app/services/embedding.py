from langchain_ollama import OllamaEmbeddings
from app.core.config import settings
from typing import List

class EmbeddingService:
    def __init__(self, model_name: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        """
        Initializes the local embedding service using LangChain and Ollama.
        """
        self.embeddings = OllamaEmbeddings(
            model=model_name,
            base_url=base_url
        )

    def embed_text(self, text: str) -> List[float]:
        """
        Generates a vector embedding for a single text query or document chunk.
        """
        return self.embeddings.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generates vector embeddings for a batch of document chunks.
        """
        return self.embeddings.embed_documents(texts)

# Singleton instance for easy import across endpoints and services
embedding_service = EmbeddingService(
    model_name=settings.EMBEDDING_MODEL_NAME,
    base_url=settings.OLLAMA_BASE_URL
)
