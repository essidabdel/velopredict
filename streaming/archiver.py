"""Consumer Kafka : lit velib.station_status et insère par lots dans
TimescaleDB. Les offsets ne sont commités qu'après succès de l'insertion
du lot (at-least-once ; les doublons éventuels sont absorbés par la
contrainte d'unicité (station_id, ts) de la table station_status).
"""

from __future__ import annotations

import json
import logging
import signal
import time
from datetime import UTC, datetime
from typing import Any

import psycopg2
import psycopg2.extras
from confluent_kafka import Consumer

from . import config

logger = logging.getLogger("streaming.archiver")

_shutdown = False

SOURCE_LIVE = "live"

INSERT_SQL = """
INSERT INTO station_status (
    station_id, ts, last_reported, num_mechanical, num_ebike,
    num_docks_available, is_renting, is_returning, source
) VALUES %s
ON CONFLICT (station_id, ts) DO NOTHING
"""


def _handle_signal(signum: int, _frame: Any) -> None:
    global _shutdown
    logger.info("Signal %s reçu, arrêt en cours...", signum)
    _shutdown = True


def parse_message(raw_value: bytes, offset: int) -> tuple | None:
    """Transforme la valeur JSON d'un message Kafka en tuple de colonnes
    prêt pour l'insertion. Retourne None (et logue) si le message est
    invalide, plutôt que de faire planter l'archiver."""
    try:
        payload = json.loads(raw_value)
        return (
            payload["station_id"],
            payload["collected_at"],
            datetime.fromtimestamp(payload["last_reported"], tz=UTC),
            payload["num_mechanical"],
            payload["num_ebike"],
            payload["num_docks_available"],
            bool(payload["is_renting"]),
            bool(payload["is_returning"]),
            SOURCE_LIVE,
        )
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        logger.error("Message invalide ignoré (offset %s) : %s", offset, exc)
        return None


def connect_db() -> psycopg2.extensions.connection:
    delay = 2.0
    while not _shutdown:
        try:
            conn = psycopg2.connect(config.DATABASE_URL)
            conn.autocommit = False
            logger.info("Connecté à TimescaleDB")
            return conn
        except psycopg2.OperationalError as exc:
            logger.warning(
                "TimescaleDB indisponible (%s), nouvelle tentative dans %.0fs", exc, delay
            )
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise SystemExit(0)


def insert_batch(
    conn: psycopg2.extensions.connection, rows: list[tuple]
) -> psycopg2.extensions.connection:
    """Insère le lot avec retry indéfini : le lot n'est jamais abandonné,
    il est retenté jusqu'à succès (aucune donnée perdue si TimescaleDB
    redémarre pendant l'insertion)."""
    delay = 2.0
    while not _shutdown:
        try:
            with conn.cursor() as cur:
                psycopg2.extras.execute_values(cur, INSERT_SQL, rows)
            conn.commit()
            return conn
        except psycopg2.Error as exc:
            try:
                conn.rollback()
            except psycopg2.Error:
                pass
            logger.warning(
                "Échec d'insertion du batch de %d lignes (%s), nouvelle tentative dans %.0fs",
                len(rows),
                exc,
                delay,
            )
            time.sleep(delay)
            delay = min(delay * 2, 60)
            if conn.closed:
                conn = connect_db()
    return conn


def run() -> None:
    logging.basicConfig(
        level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    conn = connect_db()
    consumer = Consumer(
        {
            "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": "velopredict-archiver",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe([config.KAFKA_TOPIC_STATION_STATUS])
    logger.info(
        "Archiver démarré (topic = %s, batch max = %d lignes / %.0fs)",
        config.KAFKA_TOPIC_STATION_STATUS,
        config.BATCH_MAX_SIZE,
        config.BATCH_MAX_SECONDS,
    )

    batch: list[tuple] = []
    batch_opened_at: float | None = None

    try:
        while not _shutdown:
            msg = consumer.poll(timeout=1.0)
            if msg is not None:
                if msg.error():
                    logger.error("Erreur Kafka : %s", msg.error())
                else:
                    row = parse_message(msg.value(), msg.offset())
                    if row is not None:
                        batch.append(row)
                        if batch_opened_at is None:
                            batch_opened_at = time.monotonic()

            batch_full = len(batch) >= config.BATCH_MAX_SIZE
            batch_timed_out = (
                batch_opened_at is not None
                and (time.monotonic() - batch_opened_at) >= config.BATCH_MAX_SECONDS
            )
            if batch and (batch_full or batch_timed_out):
                conn = insert_batch(conn, batch)
                consumer.commit(asynchronous=False)
                logger.info("Batch archivé : %d lignes", len(batch))
                batch = []
                batch_opened_at = None
    finally:
        if batch:
            conn = insert_batch(conn, batch)
            consumer.commit(asynchronous=False)
            logger.info("Batch final archivé avant arrêt : %d lignes", len(batch))
        consumer.close()
        conn.close()
        logger.info("Archiver arrêté proprement")


if __name__ == "__main__":
    run()
