from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.api.v1.endpoints import rag, documents, llm_playground
from app.core.database import engine, Base
from app.models.chunk import ChunkModel  # Register vector table in Base.metadata.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to PostgreSQL and verify pgvector extension
    print("Application starting up... Connecting to PostgreSQL & pgvector...")
    try:
        async with engine.begin() as conn:
            # Test basic connection
            await conn.execute(text("SELECT 1"))
            # Ensure pgvector extension exists
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            # Bootstrap the initial schema. For managed deployments, replace this
            # with versioned Alembic migrations before applying schema changes.
            await conn.run_sync(Base.metadata.create_all)
        print("Database connection established and pgvector extension verified successfully.")
    except Exception as e:
        print(f"Warning: Database startup check failed: {e}")
    
    yield
    
    # Shutdown: Dispose database engine
    print("Application shutting down...")
    await engine.dispose()

app = FastAPI(
    title="AegisAI Core Engine",
    description="Enterprise LLM Governance & RAG Observability Service",
    version="1.0.0",
    lifespan=lifespan
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

# Register your routers
app.include_router(rag.router, prefix="/api/v1/rag", tags=["RAG Services"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Document Management"])
app.include_router(llm_playground.router, prefix="/api/v1", tags=["LLM Playground"])
