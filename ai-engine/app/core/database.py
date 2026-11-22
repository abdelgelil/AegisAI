from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings


def normalize_database_url(database_url: str | URL) -> tuple[URL, dict]:
    """Prepare Neon URLs for asyncpg, which does not accept libpq-only options."""
    url = make_url(database_url) if isinstance(database_url, str) else database_url
    connect_args: dict = {}

    # Neon's dashboard gives "postgresql://..." (or "postgres://..."). That makes
    # SQLAlchemy load a sync driver (psycopg). Force asyncpg.
    if url.drivername in ("postgres", "postgresql"):
        url = url.set(drivername="postgresql+asyncpg")

    if url.drivername == "postgresql+asyncpg":
        query = dict(url.query)
        query.pop("sslmode", None)
        query.pop("channel_binding", None)
        query.pop("ssl", None)
        url = url.set(query=query)
        connect_args["ssl"] = "require"
        if "-pooler" in (url.host or ""):
            # Neon's PgBouncer pooler: don't cache prepared statements.
            connect_args["statement_cache_size"] = 0

    return url, connect_args


database_url, database_connect_args = normalize_database_url(settings.DATABASE_URL)
engine = create_async_engine(
    database_url,
    connect_args=database_connect_args,
    echo=settings.DB_ECHO,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


# Dependency to get DB session in FastAPI endpoints
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session