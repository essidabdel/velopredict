"""Consumer Kafka : maintient dans Redis le dernier état connu de chaque
station (lecture rapide pour l'API). Même schéma de robustesse que
streaming/archiver.py (batch + commit des offsets après écriture réussie),
mais pas de contrainte d'unicité à gérer : écrire deux fois le même état
dans Redis est inoffensif (SET écrase simplement l'ancienne valeur).
"""

from __future__ import annotations

import json
import logging
import signal
import time
from typing import Any

import redis
from confluent_kafka import Consumer

from . import config

logger = logging.getLogger("streaming.live")

_shutdown = False

STATION_KEY_PREFIX = "station:"
STATIONS_INDEX_KEY = "stations:index"


def _handle_signal(signum: int, _frame: Any) -> None:
    global _shutdown
    logger.info("Signal %s reçu, arrêt en cours...", signum)
    _shutdown = True


def parse_message(raw_value: bytes) -> dict[str, Any] | None:
    try:
        payload = json.loads(raw_value)
        if "station_id" not in payload:
            raise KeyError("station_id")
        return payload
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        logger.error("Message invalide ignoré : %s", exc)
        return None


def connect_redis() -> redis.Redis:
    delay = 2.0
    while not _shutdown:
        try:
            client = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
            client.ping()
            logger.info("Connecté à Redis")
            return client
        except redis.RedisError as exc:
            logger.warning("Redis indisponible (%s), nouvelle tentative dans %.0fs", exc, delay)
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise SystemExit(0)


def write_batch(client: redis.Redis, batch: dict[int, dict[str, Any]]) -> redis.Redis:
    """Écrit le lot avec retry indéfini : jamais abandonné, retenté jusqu'à
    succès (aucune donnée perdue si Redis redémarre pendant l'écriture)."""
    delay = 2.0
    while not _shutdown:
        try:
            pipe = client.pipeline()
            for station_id, payload in batch.items():
                pipe.set(
                    f"{STATION_KEY_PREFIX}{station_id}", json.dumps(payload, ensure_ascii=False)
                )
                pipe.sadd(STATIONS_INDEX_KEY, station_id)
            pipe.execute()
            return client
        except redis.RedisError as exc:
            logger.warning(
                "Échec d'écriture Redis (%d stations, %s), nouvelle tentative dans %.0fs",
                len(batch),
                exc,
                delay,
            )
            time.sleep(delay)
            delay = min(delay * 2, 60)
            try:
                client.ping()
            except redis.RedisError:
                client = connect_redis()
    return client


def run() -> None:
    logging.basicConfig(
        level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    client = connect_redis()
    consumer = Consumer(
        {
            "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": "velopredict-live",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe([config.KAFKA_TOPIC_STATION_STATUS])
    logger.info(
        "Live démarré (topic = %s, batch max = %d lignes / %.0fs)",
        config.KAFKA_TOPIC_STATION_STATUS,
        config.BATCH_MAX_SIZE,
        config.BATCH_MAX_SECONDS,
    )

    batch: dict[int, dict[str, Any]] = {}
    batch_opened_at: float | None = None

    try:
        while not _shutdown:
            msg = consumer.poll(timeout=1.0)
            if msg is not None:
                if msg.error():
                    logger.error("Erreur Kafka : %s", msg.error())
                else:
                    payload = parse_message(msg.value())
                    if payload is not None:
                        batch[payload["station_id"]] = payload
                        if batch_opened_at is None:
                            batch_opened_at = time.monotonic()

            batch_full = len(batch) >= config.BATCH_MAX_SIZE
            batch_timed_out = (
                batch_opened_at is not None
                and (time.monotonic() - batch_opened_at) >= config.BATCH_MAX_SECONDS
            )
            if batch and (batch_full or batch_timed_out):
                client = write_batch(client, batch)
                consumer.commit(asynchronous=False)
                logger.info("Batch écrit dans Redis : %d stations", len(batch))
                batch = {}
                batch_opened_at = None
    finally:
        if batch:
            client = write_batch(client, batch)
            consumer.commit(asynchronous=False)
            logger.info("Batch final écrit avant arrêt : %d stations", len(batch))
        consumer.close()
        logger.info("Live arrêté proprement")


if __name__ == "__main__":
    run()
