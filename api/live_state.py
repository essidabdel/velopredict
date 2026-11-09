"""Fusion des données statiques (Postgres) et de l'état temps réel (Redis),
et classification de l'état d'une station. Logique pure, testée sans
dépendre d'une vraie base ou d'un vrai Redis.
"""

from __future__ import annotations

import json
from typing import Any

import redis

# Dupliqué de streaming/live.py (clés Redis écrites par le consumer live) :
# chaque composant est packagé dans sa propre image Docker, pas de module
# partagé entre api/ et streaming/.
STATION_KEY_PREFIX = "station:"
STATIONS_INDEX_KEY = "stations:index"

ETAT_VIDE = "vide"
ETAT_PLEINE = "pleine"
ETAT_DISPONIBLE = "disponible"
ETAT_INCONNU = "inconnue"


def classify_state(live: dict[str, Any] | None) -> str:
    """Classe une station par rapport à son état temps réel :
    - "inconnue"  : aucune donnée temps réel reçue encore (service live pas
                    à jour, ou station jamais vue dans le flux Kafka)
    - "vide"      : 0 vélo disponible (prioritaire si bornes aussi à 0)
    - "pleine"    : 0 borne libre
    - "disponible": au moins un vélo et une borne libre
    """
    if live is None:
        return ETAT_INCONNU
    total_bikes = live.get("num_mechanical", 0) + live.get("num_ebike", 0)
    if total_bikes <= 0:
        return ETAT_VIDE
    if live.get("num_docks_available", 0) <= 0:
        return ETAT_PLEINE
    return ETAT_DISPONIBLE


def fetch_live_statuses(client: redis.Redis, station_ids: list[int]) -> dict[int, dict[str, Any]]:
    """Récupère en un seul aller-retour (MGET) l'état temps réel des
    stations demandées. Les stations sans état connu sont absentes du dict
    retourné (plutôt que mappées à None), pour que les appelants n'aient
    qu'à faire un `.get(station_id)`."""
    if not station_ids:
        return {}
    keys = [f"{STATION_KEY_PREFIX}{station_id}" for station_id in station_ids]
    raw_values = client.mget(keys)
    statuses: dict[int, dict[str, Any]] = {}
    for station_id, raw in zip(station_ids, raw_values, strict=True):
        if raw is None:
            continue
        try:
            statuses[station_id] = json.loads(raw)
        except (TypeError, ValueError):
            continue
    return statuses


def fetch_all_live_station_ids(client: redis.Redis) -> list[int]:
    return [int(station_id) for station_id in client.smembers(STATIONS_INDEX_KEY)]
