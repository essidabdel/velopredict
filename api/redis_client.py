"""Client Redis partagé (lecture de l'état temps réel des stations)."""

from __future__ import annotations

import redis

from . import config

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Dépendance FastAPI : fournit le client Redis partagé (redis-py gère
    son propre pool de connexions en interne, pas besoin d'en recréer un)."""
    global _client
    if _client is None:
        _client = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
    return _client
