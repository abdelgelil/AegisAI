"""LLM-as-a-judge evaluation for relevance and factual grounding."""

from __future__ import annotations

import json
import re
import asyncio
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

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            return json.dumps(content)
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    value = item.get("text", item.get("content", ""))
                    parts.append(str(value))
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content)

    @staticmethod
    def _normalize_score(value: Any) -> float:
        if isinstance(value, str):
            value = value.strip().rstrip("%")
        score = float(value)
        if score > 1.0 and score <= 100.0:
            score /= 100.0
        if not 0.0 <= score <= 1.0:
            raise ValueError("judge scores must be between 0 and 1, or 0 and 100 percent")
        return score

    @classmethod
    def _parse_scores(cls, content: Any) -> dict[str, float]:
        """Extract scores from JSON, fenced JSON, or common labeled prose."""
        text = cls._content_to_text(content).strip()
        names = ("context_relevance", "faithfulness", "answer_relevance")

        # Prefer strict JSON, including JSON wrapped in Markdown or commentary.
        decoder = json.JSONDecoder()
        for match in re.finditer(r"\{", text):
            try:
                raw, _ = decoder.raw_decode(text[match.start():])
            except json.JSONDecodeError:
                continue
            if isinstance(raw, dict) and all(name in raw for name in names):
                return {name: cls._normalize_score(raw[name]) for name in names}

        # Local models sometimes emit: Faithfulness: 0.82 or 82%.
        scores: dict[str, float] = {}
        for name in names:
            label = name.replace("_", r"[ _-]")
            match = re.search(
                rf"(?:\*\*|`)?{label}(?:\*\*|`)?\s*[:=\-]\s*"
                rf"(\d+(?:\.\d+)?)(?:\s*%)?",
                text,
                re.IGNORECASE,
            )
            if match:
                scores[name] = cls._normalize_score(match.group(1))
        if len(scores) == len(names):
            return scores
        raise ValueError("judge response did not contain all required evaluation scores")

    async def evaluate(self, question: str, context: str, answer: str) -> dict[str, float]:
        prompt = f"""You are a strict RAG quality evaluator. Score the supplied response using only the supplied context.
Return a JSON object with numeric values from 0.0 to 1.0 for exactly these keys:
context_relevance (how relevant the context is to the question),
faithfulness (split the answer into factual claims and judge each sentence against the context; penalize every unsupported claim),
answer_relevance (how directly the answer addresses the question).
Use 0 when there is no evidence. Do not reward plausible unsupported claims.

QUESTION:\n{question}\n\nCONTEXT:\n{context}\n\nANSWER:\n{answer}"""
        try:
            result = await asyncio.wait_for(
                self.json_llm.ainvoke(prompt),
                timeout=settings.RAG_EVALUATION_TIMEOUT_SECONDS,
            )
            return self._parse_scores(result.content)
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
