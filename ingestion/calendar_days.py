"""Charge les jours fériés (calendrier.api.gouv.fr) et les vacances
scolaires zone C de Paris (data.education.gouv.fr) dans la table
`calendar_days`. Relançable sans créer de doublons : upsert sur `day`,
chaque source ne touchant que ses propres colonnes (voir migration 002).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

from . import config
from .http_utils import fetch_json_with_retry

logger = logging.getLogger("ingestion.calendar_days")

PARIS_TZ = ZoneInfo("Europe/Paris")
PAGE_SIZE = 100

# Exclut les entrées qui ne concernent que les enseignants (pré-rentrée
# estivale) : ce ne sont pas des jours sans classe pour les élèves.
SCHOOL_HOLIDAY_POPULATIONS = {"-", "Élèves"}

HOLIDAYS_UPSERT_SQL = """
INSERT INTO calendar_days (day, is_public_holiday, holiday_name)
VALUES %s
ON CONFLICT (day) DO UPDATE SET
    is_public_holiday = EXCLUDED.is_public_holiday,
    holiday_name       = EXCLUDED.holiday_name
"""

SCHOOL_HOLIDAYS_UPSERT_SQL = """
INSERT INTO calendar_days (day, is_school_holiday, school_holiday_name)
VALUES %s
ON CONFLICT (day) DO UPDATE SET
    is_school_holiday   = EXCLUDED.is_school_holiday,
    school_holiday_name = EXCLUDED.school_holiday_name
"""


def local_date_range(start_iso: str, end_iso: str) -> list[date]:
    """Convertit [start_iso, end_iso) (horodatages UTC du jeu de données)
    en liste de dates calendaires Europe/Paris, bornes incluses à gauche
    et exclues à droite (l'API encode minuit local en UTC, donc il faut
    repasser par le fuseau pour retrouver le bon jour)."""
    start_local = datetime.fromisoformat(start_iso).astimezone(PARIS_TZ).date()
    end_local = datetime.fromisoformat(end_iso).astimezone(PARIS_TZ).date()
    nb_days = (end_local - start_local).days
    return [start_local + timedelta(days=offset) for offset in range(nb_days)]


def load_public_holidays(conn: psycopg2.extensions.connection) -> int:
    payload = fetch_json_with_retry(
        config.JOURS_FERIES_URL, logger=logger, label="jours fériés", max_attempts=5
    )
    rows = [
        (datetime.strptime(day_str, "%Y-%m-%d").date(), True, name)
        for day_str, name in payload.items()
    ]
    with conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, HOLIDAYS_UPSERT_SQL, rows)
    return len(rows)


def fetch_school_holiday_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    offset = 0
    while True:
        payload = fetch_json_with_retry(
            config.SCOLAIRE_CALENDAR_URL,
            logger=logger,
            label="vacances scolaires",
            max_attempts=5,
            params={
                "where": 'zones="Zone C" and location="Paris"',
                "limit": PAGE_SIZE,
                "offset": offset,
            },
        )
        batch = payload.get("results", [])
        records.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return records


def load_school_holidays(conn: psycopg2.extensions.connection) -> int:
    records = fetch_school_holiday_records()
    days: dict[date, str] = {}
    for record in records:
        if record.get("population") not in SCHOOL_HOLIDAY_POPULATIONS:
            continue
        for day in local_date_range(record["start_date"], record["end_date"]):
            days[day] = record["description"]

    rows = [(day, True, name) for day, name in sorted(days.items())]
    with conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, SCHOOL_HOLIDAYS_UPSERT_SQL, rows)
    return len(rows)


def load_calendar() -> None:
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL n'est pas défini (voir .env)")

    conn = psycopg2.connect(config.DATABASE_URL)
    try:
        nb_holidays = load_public_holidays(conn)
        logger.info("%d jours fériés chargés/mis à jour", nb_holidays)

        nb_school_days = load_school_holidays(conn)
        logger.info(
            "%d jours de vacances scolaires (zone C, Paris) chargés/mis à jour", nb_school_days
        )
    finally:
        conn.close()


def main() -> None:
    logging.basicConfig(
        level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    load_calendar()


if __name__ == "__main__":
    main()
