"""Bounded LangGraph retrieve/generate/evaluate/self-correction workflow."""

from __future__ import annotations

import asyncio
from typing import Any, TypedDict
import uuid

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding import embedding_service
from app.services.evaluator import RAGEvaluator
from app.services.local_llm import LocalLLMService
from app.services.vector_store import similarity_search


class RAGState(TypedDict, total=False):
    db: AsyncSession
    project_id: uuid.UUID
    query: str
    original_query: str
    top_k: int
    retry_count: int
    max_retries: int
    query_vector: list[float]
    retrieved: list[dict[str, Any]]
    context: str
    answer: str
    scores: dict[str, float]
    gate_decision: str
    block_reason: str | None
    next_step: str


class RAGWorkflow:
    def __init__(self, faithfulness_threshold: float = 0.7, max_retries: int = 1) -> None:
        self.threshold = faithfulness_threshold
        self.max_retries = max_retries
        self.llm = LocalLLMService()
        self.evaluator = RAGEvaluator()
        builder = StateGraph(RAGState)
        builder.add_node("retrieve", self.retrieve)
        builder.add_node("generate", self.generate)
        builder.add_node("evaluate", self.evaluate)
        builder.add_node("circuit_breaker", self.circuit_breaker)
        builder.set_entry_point("retrieve")
        builder.add_edge("retrieve", "generate")
        builder.add_edge("generate", "evaluate")
        builder.add_edge("evaluate", "circuit_breaker")
        builder.add_conditional_edges(
            "circuit_breaker", self.next_node,
            {"retry": "retrieve", "done": END},
        )
        self.graph = builder.compile()

    async def retrieve(self, state: RAGState) -> dict[str, Any]:
        vector = await asyncio.to_thread(embedding_service.embed_text, state["query"])
        matches = await similarity_search(state["db"], state["project_id"], vector, state["top_k"])
        retrieved = []
        blocks = []
        for chunk, score in matches:
            metadata = chunk.metadata_json or {}
            citation = {
                "chunk_id": str(chunk.id),
                "source_filename": metadata.get("source_filename", "unknown"),
                "page_number": metadata.get("page_number"),
                "section_header": metadata.get("section_header"),
                "text": chunk.text,
                "score": score,
            }
            retrieved.append(citation)
            blocks.append(
                f"[chunk_id={citation['chunk_id']} source={citation['source_filename']} "
                f"page={citation['page_number']} section={citation['section_header']}]\n{chunk.text}"
            )
        return {"query_vector": vector, "retrieved": retrieved, "context": "\n\n".join(blocks)}

    async def generate(self, state: RAGState) -> dict[str, Any]:
        if not state.get("context"):
            return {"answer": "I could not find relevant source material to answer this question."}
        answer = await self.llm.generate_response(context=state["context"], question=state["original_query"])
        if not isinstance(answer, str):
            answer = str(answer)
        return {"answer": answer}

    async def evaluate(self, state: RAGState) -> dict[str, Any]:
        scores = await self.evaluator.evaluate(
            question=state["original_query"], context=state.get("context", ""), answer=state.get("answer", "")
        )
        return {"scores": scores}

    async def circuit_breaker(self, state: RAGState) -> dict[str, Any]:
        faithfulness = state.get("scores", {}).get("faithfulness", 0.0)
        if faithfulness >= self.threshold:
            return {"gate_decision": "PASS", "block_reason": None, "next_step": "done"}
        if state.get("retry_count", 0) < state.get("max_retries", self.max_retries):
            rewritten = await self.evaluator.reformulate(state["original_query"], state.get("context", ""))
            return {
                "query": rewritten,
                "retry_count": state.get("retry_count", 0) + 1,
                "next_step": "retry",
            }
        return {
            "answer": "I could not verify a sufficiently grounded answer from the available sources.",
            "gate_decision": "BLOCK",
            "block_reason": f"faithfulness_below_{self.threshold:.2f}",
            "next_step": "done",
        }

    @staticmethod
    def next_node(state: RAGState) -> str:
        return state.get("next_step", "done")

    async def run(self, db: AsyncSession, project_id: uuid.UUID, query: str, top_k: int) -> RAGState:
        initial: RAGState = {
            "db": db,
            "project_id": project_id,
            "query": query,
            "original_query": query,
            "top_k": top_k,
            "retry_count": 0,
            "max_retries": self.max_retries,
            "retrieved": [],
            "context": "",
            "answer": "",
            "scores": {},
        }
        return await self.graph.ainvoke(initial)
