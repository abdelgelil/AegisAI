"""Async pgvector persistence and cosine similarity retrieval."""

from __future__ import annotations

from typing import Any, Sequence
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import ChunkModel


class VectorStoreError(RuntimeError):
    """Raised when a vector operation cannot be completed safely."""


async def find_existing_chunks(
    db: AsyncSession, project_id: uuid.UUID, candidates: Sequence[dict[str, Any]]
) -> dict[str, ChunkModel]:
    """Look up exact duplicates and prior source positions before embedding."""
    if not candidates:
        return {}
    hashes = {item["content_hash"] for item in candidates}
    source_keys = {item["source_key"] for item in candidates}
    result = await db.execute(
        select(ChunkModel).where(
            ChunkModel.project_id == project_id,
            (ChunkModel.content_hash.in_(hashes) | ChunkModel.source_key.in_(source_keys)),
        )
    )
    existing: dict[str, ChunkModel] = {}
    for row in result.scalars():
        existing[f"hash:{row.content_hash}"] = row
        existing[f"source:{row.source_key}"] = row
    return existing


async def upsert_chunks(db: AsyncSession, rows: Sequence[dict[str, Any]]) -> None:
    """Insert prepared chunks and replace content at a previously seen source position."""
    from sqlalchemy.dialects.postgresql import insert

    if not rows:
        return
    stmt = insert(ChunkModel).values(list(rows))
    stmt = stmt.on_conflict_do_update(
        constraint="uq_chunk_project_source_key",
        set_={
            "text": stmt.excluded.text,
            "embedding": stmt.excluded.embedding,
            "metadata_json": stmt.excluded.metadata_json,
            "content_hash": stmt.excluded.content_hash,
            "position": stmt.excluded.position,
            "created_at": stmt.excluded.created_at,
        },
    )
    try:
        await db.execute(stmt)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise VectorStoreError("Chunk upsert failed") from exc


async def similarity_search(
    db: AsyncSession,
    project_id: uuid.UUID,
    query_vector: Sequence[float],
    top_k: int = 5,
) -> list[tuple[ChunkModel, float]]:
    """Return chunks ordered by cosine similarity and normalized scores [0, 1]."""
    if len(query_vector) != 768:
        raise VectorStoreError(f"Expected 768 embedding dimensions, got {len(query_vector)}")
    distance = ChunkModel.embedding.cosine_distance(list(query_vector)).label("distance")
    result = await db.execute(
        select(ChunkModel, distance)
        .where(ChunkModel.project_id == project_id)
        .order_by(distance)
        .limit(max(1, min(top_k, 50)))
    )
    return [(chunk, max(0.0, min(1.0, 1.0 - float(distance_value))))
            for chunk, distance_value in result.all()]
