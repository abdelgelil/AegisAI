from langchain_ollama import ChatOllama
from app.core.config import settings

class LocalLLMService:
    def __init__(self, model_name: str = settings.LLM_MODEL_NAME, base_url: str = settings.OLLAMA_BASE_URL):
        self.llm = ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=0.1,  # Low temperature for factual RAG groundedness
        )

    async def generate_response(self, context: str, question: str) -> str:
        """
        Generates an answer using the local Llama model given retrieved context and a question.
        """
        prompt = f"""You are an enterprise AI assistant for AegisAI. Answer the user question strictly based on the provided context. If the answer cannot be found in the context, state that you do not know.

Context:
{context}

Question:
{question}

Answer:"""
        
        response = await self.llm.ainvoke(prompt)
        content = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        return str(content)
