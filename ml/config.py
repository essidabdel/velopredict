"""Configuration partagée des scripts ML (chargée depuis .env)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

MODELS_DIR = Path(__file__).resolve().parent / "models"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://velopredict:admin@localhost:5433/velopredict"
)
LOG_LEVEL = _env("LOG_LEVEL", "INFO")


def get_engine() -> Engine:
    url = DATABASE_URL
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    return create_engine(url)
