"""LLM-as-a-judge evaluation for relevance and factual grounding."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_ollama import ChatOllama

from app.core.config import settings


class EvaluationError(RuntimeError):
    """Raised when the evaluator cannot return validated metric scores."""


class RAGEvaluator:
    def __init__(self) -> None:
        self.llm = ChatOllama(
            model=settings.LLM_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.0,
        )
        self.json_llm = ChatOllama(
            model=settings.LLM_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.0,
            format="json",
        )

    async def evaluate(self, question: str, context: str, answer: str) -> dict[str, float]:
        prompt = f"""You are a strict RAG quality evaluator. Score the supplied response using only the supplied context.
Return a JSON object with numeric values from 0.0 to 1.0 for exactly these keys:
context_relevance (how relevant the context is to the question),
faithfulness (split the answer into factual claims and judge each sentence against the context; penalize every unsupported claim),
answer_relevance (how directly the answer addresses the question).
Use 0 when there is no evidence. Do not reward plausible unsupported claims.

QUESTION:\n{question}\n\nCONTEXT:\n{context}\n\nANSWER:\n{answer}"""
        try:
            result = await self.json_llm.ainvoke(prompt)
            content: Any = result.content
            if not isinstance(content, str):
                content = str(content)
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise ValueError("judge response did not contain a JSON object")
            raw = json.loads(match.group(0))
            names = ("context_relevance", "faithfulness", "answer_relevance")
            scores = {name: float(raw[name]) for name in names}
            if any(not 0.0 <= score <= 1.0 for score in scores.values()):
                raise ValueError("judge scores must be between 0 and 1")
            return scores
        except Exception as exc:
            raise EvaluationError("RAG evaluation failed") from exc

    async def reformulate(self, question: str, context: str) -> str:
        prompt = f"""Rewrite the user question as one concise retrieval search query that may find evidence in the supplied documents.
Return only the rewritten query. Preserve the user's intent. Do not answer the question.

Question: {question}
Available context: {context[:3000]}"""
        result = await self.llm.ainvoke(prompt)
        content = result.content
        rewritten = content.strip() if isinstance(content, str) else str(content).strip()
        if not rewritten:
            return question
        return rewritten[:1000]
