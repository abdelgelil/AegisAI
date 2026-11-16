"""Aggregate API v1 routers while preserving their existing URL prefixes."""

from fastapi import APIRouter

from app.api.v1.endpoints import documents, gateway, llm_playground, rag


router = APIRouter()
router.include_router(gateway.router, tags=["AI Gateway"])
router.include_router(rag.router, prefix="/rag", tags=["RAG Services"])
router.include_router(documents.router, prefix="/documents", tags=["Document Management"])
router.include_router(llm_playground.router, tags=["LLM Playground"])
