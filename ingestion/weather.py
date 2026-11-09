"""Charge l'historique météo Open-Meteo (depuis le début de la collecte)
puis les prévisions horaires à venir, dans la table `weather`. Relançable
sans créer de doublons : upsert sur `ts`, où une prévision ne peut jamais
écraser un relevé archive déjà confirmé pour la même heure (voir
UPSERT_SQL et la migration 002).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

from . import config
from .http_utils import fetch_json_with_retry

logger = logging.getLogger("ingestion.weather")

PARIS_TZ = ZoneInfo("Europe/Paris")
FORECAST_DAYS_AHEAD = 7
HOURLY_VARS = "temperature_2m,precipitation,wind_speed_10m"

UPSERT_SQL = """
INSERT INTO weather (ts, temperature_c, precipitation_mm, wind_speed_kmh, source)
VALUES %s
ON CONFLICT (ts) DO UPDATE SET
    temperature_c    = EXCLUDED.temperature_c,
    precipitation_mm = EXCLUDED.precipitation_mm,
    wind_speed_kmh   = EXCLUDED.wind_speed_kmh,
    source           = EXCLUDED.source,
    updated_at       = now()
WHERE weather.source = 'forecast' OR EXCLUDED.source = 'archive'
"""


def rows_from_payload(payload: dict[str, Any], source: str) -> list[tuple]:
    hourly = payload["hourly"]
    rows = []
    for ts_str, temp, precip, wind in zip(
        hourly["time"],
        hourly["temperature_2m"],
        hourly["precipitation"],
        hourly["wind_speed_10m"],
        strict=True,
    ):
        local_dt = datetime.fromisoformat(ts_str).replace(tzinfo=PARIS_TZ)
        rows.append((local_dt, temp, precip, wind, source))
    return rows


def fetch_archive(start: date, end: date) -> dict[str, Any]:
    return fetch_json_with_retry(
        config.OPEN_METEO_ARCHIVE_URL,
        logger=logger,
        label="Open-Meteo archive",
        max_attempts=5,
        params={
            "latitude": config.PARIS_LAT,
            "longitude": config.PARIS_LON,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": HOURLY_VARS,
            "timezone": "Europe/Paris",
        },
    )


def fetch_forecast(days_ahead: int) -> dict[str, Any]:
    return fetch_json_with_retry(
        config.OPEN_METEO_FORECAST_URL,
        logger=logger,
        label="Open-Meteo forecast",
        max_attempts=5,
        params={
            "latitude": config.PARIS_LAT,
            "longitude": config.PARIS_LON,
            "hourly": HOURLY_VARS,
            "timezone": "Europe/Paris",
            "forecast_days": days_ahead,
        },
    )


def resolve_backfill_start_date(conn: psycopg2.extensions.connection) -> date | None:
    """Date du premier relevé déjà collecté (début de la fenêtre à
    rapatrier) — None si station_status est encore vide."""
    with conn.cursor() as cur:
        cur.execute("SELECT min(ts)::date FROM station_status")
        (min_ts,) = cur.fetchone()
    return min_ts


def upsert_rows(conn: psycopg2.extensions.connection, rows: list[tuple]) -> None:
    if not rows:
        return
    with conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, UPSERT_SQL, rows)


def load_weather() -> None:
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL n'est pas défini (voir .env)")

    conn = psycopg2.connect(config.DATABASE_URL)
    try:
        start = resolve_backfill_start_date(conn)
        yesterday = datetime.now(UTC).date() - timedelta(days=1)

        if start is not None and start <= yesterday:
            logger.info("Backfill historique Open-Meteo du %s au %s", start, yesterday)
            rows = rows_from_payload(fetch_archive(start, yesterday), source="archive")
            upsert_rows(conn, rows)
            logger.info("%d heures historiques chargées/mises à jour", len(rows))
        else:
            logger.info(
                "Pas de backfill nécessaire (collecte démarrée aujourd'hui, ou station_status vide)"
            )

        logger.info("Chargement des prévisions à %d jours", FORECAST_DAYS_AHEAD)
        rows = rows_from_payload(fetch_forecast(FORECAST_DAYS_AHEAD), source="forecast")
        upsert_rows(conn, rows)
        logger.info("%d heures de prévisions chargées/mises à jour", len(rows))
    finally:
        conn.close()


def main() -> None:
    logging.basicConfig(
        level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    load_weather()


if __name__ == "__main__":
    main()
