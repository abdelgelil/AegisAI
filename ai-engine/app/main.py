from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.database import engine, Base
from app.models.audit import AuditLog  # Register audit table in Base.metadata.
from app.models.chunk import DocumentChunk  # Register vector table in Base.metadata.
from app.models import document as _document_models  # Register legacy document tables.

@asynccontextmanager
async def lifespan(app: FastAPI):
    from redis.asyncio import Redis

    app.state.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await app.state.redis.ping()
        print("Redis connection verified.")
    except Exception as e:
        print(f"Warning: Redis startup check failed: {e}")

    # Startup: Connect to PostgreSQL and verify pgvector extension
    print("Application starting up... Connecting to PostgreSQL & pgvector...")
    try:
        async with engine.begin() as conn:
            # Test basic connection
            await conn.execute(text("SELECT 1"))
            if settings.DB_BOOTSTRAP_ON_STARTUP:
                # Ensure pgvector extension exists
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                # Bootstrap the initial schema. For managed deployments, replace this
                # with versioned Alembic migrations before applying schema changes.
                await conn.run_sync(Base.metadata.create_all)
        print("Database connection established successfully.")
    except Exception as e:
        print(f"Warning: Database startup check failed: {e}")

    yield

    # Shutdown: Close Redis & dispose database engine
    print("Application shutting down...")
    try:
        await app.state.redis.aclose()
    except Exception as e:
        print(f"Error closing Redis connection: {e}")
    finally:
        await engine.dispose()

app = FastAPI(
    title="AegisAI Core Engine",
    description="Enterprise LLM Governance & RAG Observability Service",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-Provider-Api-Key"],
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": "AegisAI Engine"}


@app.get("/healthz", tags=["Health Check"])
async def healthz():
    """Check live database, pgvector extension, and Redis availability."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            vector_result = await conn.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            )
            vector_active = bool(vector_result.scalar())
        await app.state.redis.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="AegisAI dependencies are unavailable") from exc

    if not vector_active:
        raise HTTPException(status_code=503, detail="Required pgvector extension is unavailable")
    return {"status": "healthy", "database": "healthy", "pgvector": "healthy", "redis": "healthy"}

@app.get("/api/v1/db-check", tags=["Health Check"])
async def db_check():
    """Quick check endpoint to verify PostgreSQL connection and active pgvector extension."""
    try:
        async with engine.connect() as conn:
            version_res = await conn.execute(text("SELECT version();"))
            db_version = version_res.scalar()

            ext_res = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';"))
            vector_active = ext_res.scalar() is not None

            return {
                "status": "healthy",
                "database_version": db_version,
                "pgvector_extension_active": vector_active
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(e)}"
        )
# Register the versioned API as one aggregate, preserving existing endpoints.
app.include_router(api_v1_router, prefix="/api/v1")