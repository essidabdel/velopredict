"""Configuration de l'API (chargée depuis .env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://velopredict:admin@localhost:5433/velopredict",
)
REDIS_URL = _env("REDIS_URL", "redis://:change-me@localhost:6379/0")
LOG_LEVEL = _env("LOG_LEVEL", "INFO")
API_HOST = _env("API_HOST", "0.0.0.0")
API_PORT = int(_env("API_PORT", "8000"))
