#!/usr/bin/env python3
"""Diagnose Docker, PostgreSQL TCP access, asyncpg, and pgvector for AegisAI.

From the ai-engine directory:
    python diagnose.py

From the repository root:
    python ai-engine\diagnose.py
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR if (SCRIPT_DIR / "docker-compose.yml").exists() else SCRIPT_DIR.parent
BACKEND = ROOT / "ai-engine"
COLORS = {"PASS": "\033[32m", "WARN": "\033[33m", "FAIL": "\033[31m", "SKIP": "\033[36m", "RESET": "\033[0m"}
COLOR_ENABLED = sys.stdout.isatty() and "NO_COLOR" not in os.environ
failures = 0


def report(level: str, name: str, message: str) -> None:
    global failures
    if level == "FAIL":
        failures += 1
    tag = f"[{level}]"
    if COLOR_ENABLED:
        tag = f"{COLORS[level]}{tag}{COLORS['RESET']}"
    print(f"{tag} {name}: {message}")


def run(command: list[str], timeout: int = 15) -> subprocess.CompletedProcess[str]:
    """Run an external diagnostic command with captured errors and a timeout."""
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 127, "", str(exc))


def read_dotenv(path: Path) -> dict[str, str]:
    """Read simple KEY=value entries without evaluating shell expressions."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^export\s+", "", line)
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


async def tcp_check(host: str, port: int, timeout: float = 4.0) -> tuple[bool, str]:
    """Test raw TCP connectivity using asyncio, without a database driver."""
    try:
        _reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
        writer.close()
        await writer.wait_closed()
        return True, "connected"
    except (OSError, asyncio.TimeoutError) as exc:
        return False, str(exc)


def compose_postgres_health(docker: str, compose_file: Path, service: str) -> tuple[str, str]:
    """Inspect the selected Compose service and require running/healthy state."""
    result = run([docker, "compose", "-f", str(compose_file), "ps", "--format", "json", service])
    if result.returncode != 0:
        return "FAIL", (result.stderr or result.stdout).strip() or "compose ps failed"
    output = result.stdout.strip()
    if not output:
        return "FAIL", f"service '{service}' has no container"
    # Docker Compose emits either a JSON array or one JSON object per line.
    import json
    try:
        rows = json.loads(output) if output.startswith("[") else [json.loads(line) for line in output.splitlines() if line.strip()]
    except json.JSONDecodeError:
        return "FAIL", f"could not parse Compose status: {output}"
    if not rows:
        return "FAIL", f"service '{service}' has no container"
    states = []
    for row in rows:
        state = str(row.get("State", row.get("state", "unknown"))).lower()
        health = str(row.get("Health", row.get("health", ""))).lower()
        name = row.get("Name", row.get("Service", service))
        if state != "running":
            states.append(f"{name}: {state}")
        elif health and health != "healthy":
            states.append(f"{name}: running, health={health}")
        elif health == "healthy":
            states.append(f"{name}: running, healthy")
        else:
            # Compose reports no health status if the service has no healthcheck.
            states.append(f"{name}: running (no healthcheck configured)")
    all_running = all(str(row.get("State", row.get("state", ""))).lower() == "running" for row in rows)
    health_values = [str(row.get("Health", row.get("health", ""))).lower() for row in rows]
    all_healthy = all(value == "healthy" for value in health_values)
    no_healthcheck = any(not value for value in health_values)
    if not all_running:
        return "FAIL", "; ".join(states)
    if all_healthy:
        return "PASS", "; ".join(states)
    if no_healthcheck and all(value in ("healthy", "") for value in health_values):
        return "WARN", "; ".join(states)
    return "FAIL", "; ".join(states)


async def verify_database(database_url: str) -> None:
    """Connect with asyncpg and verify server version and pgvector activation."""
    try:
        import asyncpg  # type: ignore[import-not-found]
    except ImportError:
        report("FAIL", "Async SQL / pgvector", "asyncpg is missing; activate the backend venv and run: pip install asyncpg")
        return

    parsed = urlparse(database_url)
    # asyncpg expects a PostgreSQL URL scheme without SQLAlchemy's driver suffix.
    dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = None
    try:
        connection = await asyncpg.connect(dsn=dsn, timeout=6)
        version = await connection.fetchval("SELECT version()")
        vector_active = await connection.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        report("PASS", "Database query", str(version).splitlines()[0])
        if vector_active:
            report("PASS", "pgvector extension", "vector is active in pg_extension")
        else:
            report("FAIL", "pgvector extension", "vector is not active; enable it with CREATE EXTENSION vector")
    except Exception as exc:  # Surface connection/auth/query errors as a diagnostic result.
        report("FAIL", "Async SQL / pgvector", f"{type(exc).__name__}: {exc}")
    finally:
        if connection is not None:
            await connection.close()


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=str(BACKEND / ".env"), help="backend .env file (default: ai-engine/.env)")
    parser.add_argument("--compose-file", default=str(ROOT / "docker-compose.yml"), help="project Docker Compose file")
    parser.add_argument("--service", default="postgres", help="PostgreSQL service name in Compose")
    parser.add_argument("--host", default="127.0.0.1", help="host address to use for TCP test")
    parser.add_argument("--port", type=int, default=5432, help="published PostgreSQL TCP port")
    args = parser.parse_args()
    env_path = Path(args.env_file).resolve()
    compose_file = Path(args.compose_file).resolve()

    print("AegisAI FastAPI / PostgreSQL diagnostics")
    print(f"Project: {ROOT}")
    print(f"Backend env: {env_path}")

    if env_path.is_file():
        report("PASS", ".env file", "exists")
    else:
        report("FAIL", ".env file", "missing; create ai-engine/.env with DATABASE_URL")
    env = read_dotenv(env_path)
    database_url = os.environ.get("DATABASE_URL") or env.get("DATABASE_URL", "")

    if not database_url:
        report("FAIL", "DATABASE_URL", "not set in process environment or .env")
        parsed = None
    else:
        parsed = urlparse(database_url)
        valid = (parsed.scheme == "postgresql+asyncpg" and parsed.hostname is not None
                 and parsed.username is not None and parsed.path.strip("/") != "")
        if valid:
            report("PASS", "DATABASE_URL format", f"async SQLAlchemy URL; database={parsed.path.strip('/')}")
        else:
            report("FAIL", "DATABASE_URL format", "expected postgresql+asyncpg://user:password@host:port/database")

    if compose_file.is_file():
        report("PASS", "Compose file", str(compose_file))
    else:
        report("FAIL", "Compose file", f"not found: {compose_file}")

    docker = shutil.which("docker")
    docker_ready = False
    if not docker:
        report("FAIL", "Docker daemon", "Docker CLI not found on PATH")
    else:
        info = run([docker, "info", "--format", "{{.ServerVersion}}"], timeout=20)
        if info.returncode == 0 and info.stdout.strip():
            docker_ready = True
            report("PASS", "Docker daemon", f"reachable; engine {info.stdout.strip()}")
        else:
            report("FAIL", "Docker daemon", (info.stderr or info.stdout).strip() or "Docker engine is not reachable")

    if docker_ready and compose_file.is_file():
        level, detail = compose_postgres_health(docker, compose_file, args.service)
        report(level, f"PostgreSQL container ({args.service})", detail)
    else:
        report("SKIP", f"PostgreSQL container ({args.service})", "requires a reachable Docker daemon and Compose file")

    tcp_host = args.host
    tcp_port = args.port
    if parsed is not None:
        # Check the requested local endpoint by default; use URL port if explicitly set.
        tcp_port = parsed.port or args.port
    tcp_ok, tcp_detail = await tcp_check(tcp_host, tcp_port)
    report("PASS" if tcp_ok else "FAIL", "PostgreSQL TCP", f"{tcp_host}:{tcp_port} {tcp_detail}")

    if not database_url:
        report("SKIP", "Async SQL / pgvector", "DATABASE_URL is unavailable")
    elif parsed is None or parsed.scheme != "postgresql+asyncpg":
        report("SKIP", "Async SQL / pgvector", "DATABASE_URL format is invalid")
    elif tcp_ok:
        await verify_database(database_url)
    else:
        report("SKIP", "Async SQL / pgvector", "TCP connection failed; database query cannot run")

    print(f"\nSummary: {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
