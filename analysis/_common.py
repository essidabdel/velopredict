"""Utilitaires partagés par les notebooks d'analyse (connexion DB)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def get_engine() -> Engine:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://velopredict:change-me@localhost:5433/velopredict",
    )
    # SQLAlchemy 2.x utilise psycopg (v3) par défaut pour le schéma
    # "postgresql://" ; on force explicitement psycopg2 (déjà utilisé par
    # ingestion/streaming/api, pas besoin d'une deuxième dépendance DB).
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    return create_engine(url)
