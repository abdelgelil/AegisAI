"""Document upload and persistent vector ingestion endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.ingestion import ingest_document


router = APIRouter()
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}


@router.post("/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    project_id: UUID = Form(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Parse, deduplicate, embed, and persist a TXT, Markdown, or PDF document."""
    filename = file.filename or ""
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only .txt, .md, and .pdf uploads are supported")
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Maximum document size is 25 MiB")
        if not content:
            raise HTTPException(status_code=422, detail="Uploaded document is empty")
        result = await ingest_document(db, project_id, filename, content)
        return {"project_id": str(project_id), "filename": filename, **result}
    except HTTPException:
        raise
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse document: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Document ingestion service is unavailable") from exc
    finally:
        await file.close()
