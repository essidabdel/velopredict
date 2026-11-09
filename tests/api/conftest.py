"""Doubles de test pour la DB et Redis, injectés via les dépendances
FastAPI (app.dependency_overrides) : les tests d'endpoints tournent sans
Postgres ni Redis réels."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.db import get_db
from api.main import app
from api.redis_client import get_redis

STATIONS_FIXTURE = [
    {
        "station_id": 1,
        "name": "Benjamin Godard - Victor Hugo",
        "commune_code": "75116",
        "commune_nom": "Paris 16e Arrondissement",
        "lat": 48.865983,
        "lon": 2.275725,
        "capacity": 35,
    },
    {
        "station_id": 2,
        "name": "Mairie de Levallois",
        "commune_code": "92044",
        "commune_nom": "Levallois-Perret",
        "lat": 48.89279,
        "lon": 2.2920206,
        "capacity": 20,
    },
    {
        "station_id": 3,
        "name": "Gare du Nord",
        "commune_code": "75110",
        "commune_nom": "Paris 10e Arrondissement",
        "lat": 48.880,
        "lon": 2.355,
        "capacity": 10,
    },
]

LIVE_FIXTURE = {
    1: {
        "num_mechanical": 6,
        "num_ebike": 8,
        "num_docks_available": 21,
        "is_renting": True,
        "is_returning": True,
        "last_reported": 1700000000,
        "collected_at": "2026-11-09T18:00:00+00:00",
    },
    2: {
        "num_mechanical": 0,
        "num_ebike": 0,
        "num_docks_available": 20,
        "is_renting": True,
        "is_returning": True,
        "last_reported": 1700000001,
        "collected_at": "2026-11-09T18:00:00+00:00",
    },
    # station 3 : volontairement absente de Redis -> état "inconnue"
}

HISTORY_FIXTURE = {
    1: [
        {
            "ts": "2026-11-09T17:00:00+00:00",
            "num_mechanical": 5,
            "num_ebike": 7,
            "num_docks_available": 23,
            "is_renting": True,
            "is_returning": True,
        },
        {
            "ts": "2026-11-09T18:00:00+00:00",
            "num_mechanical": 6,
            "num_ebike": 8,
            "num_docks_available": 21,
            "is_renting": True,
            "is_returning": True,
        },
    ]
}


class FakeCursor:
    def __init__(self, stations, live, history):
        self._stations = stations
        self._live = live
        self._history = history
        self._result: list[dict] | dict | None = None

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, sql: str, params: dict | None = None) -> None:
        params = params or {}

        if "count(*) AS nb_stations" in sql:
            self._result = {"nb_stations": len(self._stations)}
            return

        if "SELECT 1 FROM stations WHERE station_id" in sql:
            match = next(
                (s for s in self._stations if s["station_id"] == params["station_id"]), None
            )
            self._result = {"exists": 1} if match else None
            return

        if "FROM station_status" in sql:
            rows = self._history.get(params["station_id"], [])
            self._result = list(rows)
            return

        if "FROM stations WHERE station_id" in sql:
            self._result = next(
                (s for s in self._stations if s["station_id"] == params["station_id"]), None
            )
            return

        if "FROM stations" in sql:
            rows = self._stations
            if "arrondissement" in params:
                needle = params["arrondissement"].strip("%").lower()
                rows = [r for r in rows if needle in r["commune_nom"].lower()]
            if "recherche" in params:
                needle = params["recherche"].strip("%").lower()
                rows = [r for r in rows if needle in r["name"].lower()]
            self._result = list(rows)
            return

        raise AssertionError(f"Requête SQL inattendue dans le test : {sql}")

    def fetchall(self):
        return self._result or []

    def fetchone(self):
        return self._result


class FakeConnection:
    def __init__(self, stations, live, history):
        self._stations = stations
        self._live = live
        self._history = history

    def cursor(self):
        return FakeCursor(self._stations, self._live, self._history)


class FakeRedis:
    def __init__(self, live: dict[int, dict]):
        self._live = live

    def mget(self, keys: list[str]):
        results = []
        for key in keys:
            station_id = int(key.split(":")[1])
            payload = self._live.get(station_id)
            results.append(json.dumps(payload) if payload else None)
        return results

    def smembers(self, _key):
        return {str(station_id) for station_id in self._live}


@pytest.fixture
def client():
    def _override_get_db():
        yield FakeConnection(STATIONS_FIXTURE, LIVE_FIXTURE, HISTORY_FIXTURE)

    def _override_get_redis():
        return FakeRedis(LIVE_FIXTURE)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = _override_get_redis
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
