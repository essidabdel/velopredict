"""Configuration partagée des consumers de streaming (chargée depuis .env).

Dupliquée volontairement par rapport à ingestion/config.py : chaque
composant (producer, archiver) est packagé dans sa propre image Docker et
ne doit pas dépendre du code d'un autre dossier.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


KAFKA_BOOTSTRAP_SERVERS = _env("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_STATION_STATUS = _env("KAFKA_TOPIC_STATION_STATUS", "velib.station_status")
LOG_LEVEL = _env("LOG_LEVEL", "INFO")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://velopredict:change-me@localhost:5432/velopredict",
)
REDIS_URL = _env("REDIS_URL", "redis://:change-me@localhost:6379/0")

# Un batch est inséré/écrit dès que l'une des deux limites est atteinte :
# ceci borne à la fois la latence et le nombre d'opérations/s en base.
BATCH_MAX_SIZE = int(_env("ARCHIVER_BATCH_MAX_SIZE", "500"))
BATCH_MAX_SECONDS = float(_env("ARCHIVER_BATCH_MAX_SECONDS", "5"))
