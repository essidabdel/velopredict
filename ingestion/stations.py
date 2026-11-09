"""Charge station_information.json dans la table de référentiel `stations`
(upsert). Script ponctuel : à lancer manuellement, ou périodiquement via
Airflow plus tard (les stations changent rarement : nom, capacité, position).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import psycopg2
import psycopg2.extras

from . import config
from .http_utils import fetch_json_with_retry

logger = logging.getLogger("ingestion.stations")

UPSERT_SQL = """
INSERT INTO stations (station_id, station_code, name, lat, lon, capacity, updated_at)
VALUES %s
ON CONFLICT (station_id) DO UPDATE SET
    station_code = EXCLUDED.station_code,
    name         = EXCLUDED.name,
    lat          = EXCLUDED.lat,
    lon          = EXCLUDED.lon,
    capacity     = EXCLUDED.capacity,
    updated_at   = EXCLUDED.updated_at
"""


def resolve_station_information_url() -> str:
    gbfs = fetch_json_with_retry(
        config.GBFS_ROOT_URL, logger=logger, label="gbfs.json", max_attempts=5
    )
    for lang_block in gbfs["data"].values():
        for feed in lang_block["feeds"]:
            if feed["name"] == "station_information":
                return feed["url"]
    raise RuntimeError("Flux 'station_information' introuvable dans gbfs.json")


def build_row(station: dict[str, Any], loaded_at: datetime) -> tuple:
    return (
        station["station_id"],
        station.get("stationCode"),
        station.get("name"),
        station.get("lat"),
        station.get("lon"),
        station.get("capacity"),
        loaded_at,
    )


def load_stations() -> int:
    url = resolve_station_information_url()
    logger.info("URL station_information résolue : %s", url)

    payload = fetch_json_with_retry(
        url, logger=logger, label="station_information.json", max_attempts=5
    )
    stations = payload["data"]["stations"]
    loaded_at = datetime.now(UTC)
    rows = [build_row(station, loaded_at) for station in stations]

    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL n'est pas défini (voir .env)")

    conn = psycopg2.connect(config.DATABASE_URL)
    try:
        with conn, conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, UPSERT_SQL, rows)
        logger.info("%d stations chargées/mises à jour dans la table 'stations'", len(rows))
    finally:
        conn.close()
    return len(rows)


def main() -> None:
    logging.basicConfig(
        level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    load_stations()


if __name__ == "__main__":
    main()
