from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse, ChunkAttribution

app = FastAPI(
    title="AegisAI Core Engine",
    description="Enterprise LLM Governance & RAG Observability Service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": "AegisAI Engine"}

@app.post("/api/v1/rag/query", response_model=RAGQueryResponse, tags=["RAG Services"])
async def process_rag_query(payload: RAGQueryRequest):
    return RAGQueryResponse(
        answer=f"Processed evaluation for query: '{payload.query}'",
        confidence_score=0.96,
        hallucination_flag=False,
        retrieved_chunks=[
            ChunkAttribution(
                chunk_id="chk_001",
                source_doc="policy.pdf",
                text_segment="Refunds require manager approval within 30 days.",
                relevance_score=0.92
            )
        ]
    )
