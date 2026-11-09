"""Backfill historique : importe l'archive communautaire ODbL
`tibzsecondaire/velib-data` (https://github.com/tibzsecondaire/velib-data,
fichiers `daily/YYYY-MM-DD.parquet` + `daily/index.csv`) dans la même
hypertable `station_status` que la collecte en direct, avec une colonne
`source` ('backfill_github' vs 'live') pour les distinguer.

Pourquoi une source tierce : le flux Vélib' officiel (GBFS) est un
instantané temps réel sans historique — il n'existe aucune archive
officielle. Ce dépôt republie les mêmes données officielles (même
`station_id`, même schéma GBFS), collectées en continu par un tiers, sous
licence ODbL (la même que le jeu officiel Paris/data.gouv.fr), avec
attribution claire. Voir le README (section Analyses) pour la justification
complète.

Qualité par jour : `daily/index.csv` donne, pour chaque jour UTC couvert,
le plus grand trou de collecte (`max_gap_minutes`). Les jours avec un trou
> `RELIABILITY_THRESHOLD_MINUTES` sont importés quand même (aucune raison
de perdre la donnée brute) mais marqués `reliable = false` dans
`backfill_day_quality`, et donc exclus de `v_training_eligible_status`
(vue utilisée pour constituer le jeu d'entraînement du modèle, Phase 5).

Rejouable sans doublon : upsert `ON CONFLICT (station_id, ts) DO NOTHING`
sur station_status (comme l'archiver), et `ON CONFLICT (day) DO UPDATE`
sur backfill_day_quality (la qualité d'un jour peut changer si l'archive
amont est corrigée).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

logger = logging.getLogger("ingestion.backfill")

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://velopredict:change-me@localhost:5433/velopredict"
)
ARCHIVE_BASE_URL = "https://raw.githubusercontent.com/tibzsecondaire/velib-data/main"
BATCH_SIZE = 5000
SOURCE_BACKFILL_GITHUB = "backfill_github"

# Jours dont le plus grand trou de collecte dépasse ce seuil : marqués
# non fiables, exclus de v_training_eligible_status (mais quand même
# importés dans station_status — la donnée brute reste utile ailleurs,
# par exemple pour les notebooks d'exploration de analysis/).
RELIABILITY_THRESHOLD_MINUTES = 60.0

INSERT_STATUS_SQL = """
INSERT INTO station_status (
    station_id, ts, last_reported, num_mechanical, num_ebike,
    num_docks_available, is_renting, is_returning, source
) VALUES %s
ON CONFLICT (station_id, ts) DO NOTHING
"""

UPSERT_DAY_QUALITY_SQL = """
INSERT INTO backfill_day_quality (day, snapshots, max_gap_minutes, reliable)
VALUES %s
ON CONFLICT (day) DO UPDATE SET
    snapshots        = EXCLUDED.snapshots,
    max_gap_minutes  = EXCLUDED.max_gap_minutes,
    reliable         = EXCLUDED.reliable
"""


def is_reliable(max_gap_minutes: float, threshold: float = RELIABILITY_THRESHOLD_MINUTES) -> bool:
    return max_gap_minutes <= threshold


def fetch_index() -> pd.DataFrame:
    return pd.read_csv(f"{ARCHIVE_BASE_URL}/daily/index.csv")


def list_available_days(index: pd.DataFrame) -> list[str]:
    return sorted(index["date"].astype(str).tolist())


def fetch_day(date: str) -> pd.DataFrame:
    return pd.read_parquet(f"{ARCHIVE_BASE_URL}/daily/{date}.parquet")


def rows_from_day(df: pd.DataFrame) -> list[tuple]:
    return [
        (
            int(r.station_id),
            r.fetched_at.to_pydatetime(),
            r.last_reported.to_pydatetime(),
            int(r.mechanical),
            int(r.ebike),
            int(r.docks),
            bool(r.is_renting),
            bool(r.is_returning),
            SOURCE_BACKFILL_GITHUB,
        )
        for r in df.itertuples(index=False)
    ]


def insert_rows(conn: psycopg2.extensions.connection, rows: list[tuple]) -> int:
    # page_size=len(chunk) force un seul INSERT par chunk : sans ça,
    # execute_values pagine en interne (défaut 100 lignes/page) et
    # cur.rowcount ne reflète que la dernière page, pas le total.
    inserted = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), BATCH_SIZE):
            chunk = rows[i : i + BATCH_SIZE]
            psycopg2.extras.execute_values(cur, INSERT_STATUS_SQL, chunk, page_size=len(chunk))
            inserted += cur.rowcount
    conn.commit()
    return inserted


def upsert_day_quality(conn: psycopg2.extensions.connection, index: pd.DataFrame) -> int:
    rows = [
        (row.date, int(row.snapshots), float(row.max_gap_minutes), is_reliable(row.max_gap_minutes))
        for row in index.itertuples(index=False)
    ]
    with conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, UPSERT_DAY_QUALITY_SQL, rows, page_size=len(rows))
    return len(rows)


def backfill_day(conn: psycopg2.extensions.connection, date: str) -> tuple[int, int]:
    df = fetch_day(date)
    rows = rows_from_day(df)
    inserted = insert_rows(conn, rows)
    return len(rows), inserted


def backfill_all() -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        index = fetch_index()
        nb_fiables = upsert_day_quality(conn, index)
        nb_non_fiables = int((~index["max_gap_minutes"].le(RELIABILITY_THRESHOLD_MINUTES)).sum())
        logger.info(
            "Qualité par jour mise à jour : %d jours (%d marqués non fiables, seuil = %.0f min)",
            nb_fiables,
            nb_non_fiables,
            RELIABILITY_THRESHOLD_MINUTES,
        )

        days = list_available_days(index)
        logger.info("%d jours disponibles dans l'archive (%s a %s)", len(days), days[0], days[-1])

        total_lues = 0
        total_inserees = 0
        for date in days:
            nb_lues, nb_inserees = backfill_day(conn, date)
            total_lues += nb_lues
            total_inserees += nb_inserees
            logger.info(
                "%s : %d lignes lues, %d inserees (cumul : %d)",
                date,
                nb_lues,
                nb_inserees,
                total_inserees,
            )
        logger.info(
            "Backfill termine : %d lignes lues, %d inserees sur %d jours",
            total_lues,
            total_inserees,
            len(days),
        )
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    backfill_all()
