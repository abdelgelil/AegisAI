"""Document parsing, recursive chunking, deduplication, and embedding."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import io
import re
import uuid
from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding import embedding_service
from app.services.vector_store import find_existing_chunks, upsert_chunks


@dataclass(frozen=True)
class ParsedPage:
    text: str
    page_number: int
    section_header: str | None = None


def _parse_file(filename: str, content: bytes) -> list[ParsedPage]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        pages = [ParsedPage(page.extract_text() or "", index + 1) for index, page in enumerate(reader.pages)]
    elif suffix in {".txt", ".md"}:
        text = content.decode("utf-8-sig")
        if suffix == ".md":
            section = ""
            current: list[str] = []
            pages = []
            for line in text.splitlines():
                heading = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
                if heading and current:
                    pages.append(ParsedPage("\n".join(current).strip(), 1, section or None))
                    current = []
                if heading:
                    section = heading.group(1).strip()
                current.append(line)
            if current:
                pages.append(ParsedPage("\n".join(current).strip(), 1, section or None))
        else:
            pages = [ParsedPage(text, 1)]
    else:
        raise ValueError("Supported document types are PDF, TXT, and Markdown")
    if not any(page.text.strip() for page in pages):
        raise ValueError("The document contains no extractable text")
    return pages


def _hash(value: str) -> str:
    normalized = " ".join(value.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _split_pages(pages: list[ParsedPage], filename: str, chunk_size: int, chunk_overlap: int) -> list[dict[str, Any]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        add_start_index=True,
    )
    output = []
    position = 0
    for page in pages:
        if not page.text.strip():
            continue
        for item in splitter.create_documents([page.text]):
            body = item.page_content.strip()
            if not body:
                continue
            chunk_id = uuid.uuid4()
            source_material = f"{filename.casefold()}|{page.page_number}|{position}"
            output.append({
                "id": chunk_id,
                "text": body,
                "position": position,
                "content_hash": _hash(body),
                "source_key": hashlib.sha256(source_material.encode()).hexdigest(),
                "metadata_json": {
                    "chunk_id": str(chunk_id),
                    "source_filename": filename,
                    "page_number": page.page_number,
                    "section_header": page.section_header,
                    "position": position,
                    "start_index": item.metadata.get("start_index", 0),
                },
            })
            position += 1
    return output


async def ingest_document(
    db: AsyncSession,
    project_id: uuid.UUID,
    filename: str,
    content: bytes,
    *,
    chunk_size: int = 1200,
    chunk_overlap: int = 160,
) -> dict[str, Any]:
    """Parse and store a document, returning inserted, duplicate, and replaced counts."""
    try:
        pages = await asyncio.to_thread(_parse_file, filename, content)
    except (UnicodeDecodeError, ValueError):
        raise
    except Exception as exc:
        raise ValueError("The uploaded file could not be parsed") from exc
    candidates = await asyncio.to_thread(_split_pages, pages, filename, chunk_size, chunk_overlap)
    prior = await find_existing_chunks(db, project_id, candidates)

    to_embed: list[dict[str, Any]] = []
    duplicate_count = 0
    replaced_count = 0
    for row in candidates:
        same_content = prior.get(f"hash:{row['content_hash']}")
        same_source = prior.get(f"source:{row['source_key']}")
        if same_content:
            row["id"] = same_content.id
            row["metadata_json"] = dict(same_content.metadata_json or row["metadata_json"])
            row["metadata_json"]["chunk_id"] = str(same_content.id)
            duplicate_count += 1
            continue
        if same_source:
            row["id"] = same_source.id
            row["metadata_json"]["chunk_id"] = str(same_source.id)
            replaced_count += 1
        to_embed.append(row)

    if to_embed:
        vectors = await asyncio.to_thread(embedding_service.embed_documents, [row["text"] for row in to_embed])
        for row, vector in zip(to_embed, vectors, strict=True):
            if len(vector) != 768:
                raise RuntimeError(f"Embedding model returned {len(vector)} dimensions; expected 768")
            row["project_id"] = project_id
            row["embedding"] = vector
        await upsert_chunks(db, to_embed)

    return {
        "total_chunks": len(candidates),
        "inserted_chunks": len(to_embed) - replaced_count,
        "replaced_chunks": replaced_count,
        "duplicate_chunks": duplicate_count,
        "chunks": [{**row["metadata_json"], "text": row["text"]} for row in candidates],
    }
