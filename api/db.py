"""Pool de connexions PostgreSQL/TimescaleDB partagé par les requêtes HTTP."""

from __future__ import annotations

from collections.abc import Iterator

import psycopg2.pool
from psycopg2.extras import RealDictCursor

from . import config

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(1, 10, dsn=config.DATABASE_URL)
    return _pool


def get_db() -> Iterator[psycopg2.extensions.connection]:
    """Dépendance FastAPI : fournit une connexion issue du pool, cursor_factory
    RealDictCursor pour manipuler les lignes comme des dicts."""
    pool = _get_pool()
    conn = pool.getconn()
    conn.cursor_factory = RealDictCursor
    try:
        yield conn
    finally:
        pool.putconn(conn)
