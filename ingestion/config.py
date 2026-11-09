"""Configuration partagée des scripts d'ingestion (chargée depuis .env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


GBFS_ROOT_URL = _env(
    "GBFS_ROOT_URL",
    "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/gbfs.json",
)
KAFKA_BOOTSTRAP_SERVERS = _env("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_STATION_STATUS = _env("KAFKA_TOPIC_STATION_STATUS", "velib.station_status")
POLL_INTERVAL_SECONDS = int(_env("INGESTION_POLL_INTERVAL_SECONDS", "60"))
LOG_LEVEL = _env("LOG_LEVEL", "INFO")

# Utilisé par ingestion/stations.py, weather.py, calendar_days.py et
# stations_geo.py (scripts d'enrichissement, pas le producer temps réel).
DATABASE_URL = os.environ.get("DATABASE_URL")

# Open-Meteo (météo horaire, point fixe Paris — cf. CLAUDE.md)
OPEN_METEO_FORECAST_URL = _env("OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
OPEN_METEO_ARCHIVE_URL = _env(
    "OPEN_METEO_ARCHIVE_URL", "https://archive-api.open-meteo.com/v1/archive"
)
PARIS_LAT = float(_env("OPEN_METEO_LAT", "48.8566"))
PARIS_LON = float(_env("OPEN_METEO_LON", "2.3522"))

# Calendriers (jours fériés + vacances scolaires)
JOURS_FERIES_URL = _env(
    "JOURS_FERIES_URL", "https://calendrier.api.gouv.fr/jours-feries/metropole.json"
)
SCOLAIRE_CALENDAR_URL = _env(
    "SCOLAIRE_CALENDAR_URL",
    "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-calendrier-scolaire/records",
)

# Géocodage inverse (commune / arrondissement) — API officielle data.gouv.fr
GEO_API_BASE_URL = _env("GEO_API_BASE_URL", "https://geo.api.gouv.fr/communes")
