"""Producer Kafka : interroge station_status.json toutes les N secondes et
publie chaque station comme un message dans le topic velib.station_status
(clé = station_id). Ne doit jamais s'arrêter sur une erreur réseau/Kafka.
"""

from __future__ import annotations

import json
import logging
import signal
import time
from datetime import UTC, datetime
from typing import Any

from confluent_kafka import Producer

from . import config
from .http_utils import fetch_json_with_retry

logger = logging.getLogger("ingestion.producer")

_shutdown = False


def _handle_signal(signum: int, _frame: Any) -> None:
    global _shutdown
    logger.info("Signal %s reçu, arrêt en cours...", signum)
    _shutdown = True


def resolve_station_status_url() -> str:
    """Lit gbfs.json et retourne l'URL réelle de station_status.json —
    on ne suppose jamais que l'URL est fixe (règle du projet)."""
    gbfs = fetch_json_with_retry(
        config.GBFS_ROOT_URL, logger=logger, label="gbfs.json", max_attempts=None
    )
    for lang_block in gbfs["data"].values():
        for feed in lang_block["feeds"]:
            if feed["name"] == "station_status":
                return feed["url"]
    raise RuntimeError("Flux 'station_status' introuvable dans gbfs.json")


def extract_bike_types(types: list[dict[str, int]] | None) -> tuple[int, int]:
    """num_bikes_available_types = [{"mechanical": N}, {"ebike": M}], mais on
    ne suppose pas l'ordre ni la présence des deux clés."""
    mechanical = 0
    ebike = 0
    for entry in types or []:
        mechanical += entry.get("mechanical", 0)
        ebike += entry.get("ebike", 0)
    return mechanical, ebike


def build_message(station: dict[str, Any], collected_at: str) -> dict[str, Any]:
    mechanical, ebike = extract_bike_types(station.get("num_bikes_available_types"))
    return {
        "station_id": station["station_id"],
        "station_code": station.get("stationCode"),
        "num_bikes_available": station.get("num_bikes_available", 0),
        "num_mechanical": mechanical,
        "num_ebike": ebike,
        "num_docks_available": station.get("num_docks_available", 0),
        "is_installed": bool(station.get("is_installed", 0)),
        "is_renting": bool(station.get("is_renting", 0)),
        "is_returning": bool(station.get("is_returning", 0)),
        "last_reported": station.get("last_reported"),
        "collected_at": collected_at,
    }


def _delivery_callback(err: Any, msg: Any) -> None:
    if err is not None:
        logger.error("Échec de publication Kafka pour la clé %s : %s", msg.key(), err)


def _run_cycle(producer: Producer, station_status_url: str) -> int:
    payload = fetch_json_with_retry(
        station_status_url, logger=logger, label="station_status.json", max_attempts=5
    )
    stations = payload["data"]["stations"]
    collected_at = datetime.now(UTC).isoformat()

    produced = 0
    for station in stations:
        message = build_message(station, collected_at)
        producer.produce(
            topic=config.KAFKA_TOPIC_STATION_STATUS,
            key=str(message["station_id"]).encode("utf-8"),
            value=json.dumps(message, ensure_ascii=False).encode("utf-8"),
            callback=_delivery_callback,
        )
        producer.poll(0)  # laisse circuler les callbacks de livraison déjà reçus
        produced += 1

    producer.flush(10)
    return produced


def run() -> None:
    logging.basicConfig(
        level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("Résolution de l'URL station_status.json via %s", config.GBFS_ROOT_URL)
    station_status_url = resolve_station_status_url()
    logger.info("URL station_status résolue : %s", station_status_url)

    producer = Producer(
        {
            "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
            "client.id": "velopredict-producer",
            "enable.idempotence": True,
            "acks": "all",
            "retries": 5,
            "linger.ms": 100,
        }
    )

    logger.info(
        "Démarrage de la boucle de collecte (intervalle = %ds, topic = %s)",
        config.POLL_INTERVAL_SECONDS,
        config.KAFKA_TOPIC_STATION_STATUS,
    )

    while not _shutdown:
        cycle_start = time.monotonic()
        try:
            produced = _run_cycle(producer, station_status_url)
            logger.info("Cycle terminé : %d stations publiées", produced)
        except Exception:  # noqa: BLE001 - ne doit jamais crasher le service
            logger.exception(
                "Erreur pendant le cycle de collecte, nouvelle tentative au prochain cycle"
            )

        elapsed = time.monotonic() - cycle_start
        remaining = max(config.POLL_INTERVAL_SECONDS - elapsed, 1)
        while remaining > 0 and not _shutdown:
            time.sleep(min(1, remaining))
            remaining -= 1

    logger.info("Flush final du producer avant arrêt")
    producer.flush(10)
    logger.info("Producer arrêté proprement")


if __name__ == "__main__":
    run()
