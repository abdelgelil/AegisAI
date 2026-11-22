-- Already applied on Neon branch "DB V1". Not yet applied on "production".
-- Run on production only after: (1) SELECT count(*) FROM document_chunks; returns 0,
-- (2) the team has been told.
-- Why: embedding model is nomic-embed-text (768 dims); the table was built for 1536.
-- Why: the Python DocumentChunk model expects project_id, document_name, is_poisoned,
-- metadata_json, source_key and two unique constraints that the ERD table lacks.
-- STOPGAP: chunks are not linked to documents yet (document_id is nullable).

BEGIN;

DROP INDEX IF EXISTS idx_chunks_embedding;
ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768);
CREATE INDEX idx_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- Requires an empty table (NOT NULL columns without defaults).
ALTER TABLE document_chunks
  ADD COLUMN project_id    uuid NOT NULL,
  ADD COLUMN document_name varchar(512),
  ADD COLUMN is_poisoned   boolean NOT NULL DEFAULT false,
  ADD COLUMN metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN source_key    varchar(64) NOT NULL;

ALTER TABLE document_chunks ALTER COLUMN document_id DROP NOT NULL;
ALTER TABLE document_chunks ALTER COLUMN content_hash TYPE varchar(64);

ALTER TABLE document_chunks
  ADD CONSTRAINT uq_chunk_project_source_key UNIQUE (project_id, source_key),
  ADD CONSTRAINT uq_chunk_project_content_hash UNIQUE (project_id, content_hash);

CREATE INDEX IF NOT EXISTS ix_document_chunks_project_id ON document_chunks (project_id);

COMMIT;
