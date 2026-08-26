from pydantic import BaseModel, Field
from typing import List, Optional

class RAGQueryRequest(BaseModel):
    query: str = Field(..., example="What is our internal refund policy?")
    session_id: Optional[str] = Field(None, example="sess_12345")

class ChunkAttribution(BaseModel):
    chunk_id: str
    source_doc: str
    text_segment: str
    relevance_score: float

class RAGQueryResponse(BaseModel):
    answer: str
    confidence_score: float
    hallucination_flag: bool
    retrieved_chunks: List[ChunkAttribution]
