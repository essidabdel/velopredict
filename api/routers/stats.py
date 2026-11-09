"""Endpoint de synthèse : vue d'ensemble du réseau."""

from __future__ import annotations

from typing import Annotated

import psycopg2.extensions
import redis
from fastapi import APIRouter, Depends

from .. import live_state
from ..db import get_db
from ..redis_client import get_redis
from ..schemas import StatsOverview

router = APIRouter(tags=["stats"])


@router.get("/stats/overview", response_model=StatsOverview)
def stats_overview(
    conn: Annotated[psycopg2.extensions.connection, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) AS nb_stations FROM stations")
        nb_stations = cur.fetchone()["nb_stations"]

    live_ids = live_state.fetch_all_live_station_ids(redis_client)
    live_statuses = live_state.fetch_live_statuses(redis_client, live_ids)

    total_mechanical = 0
    total_ebike = 0
    total_docks_available = 0
    nb_vides = 0
    nb_pleines = 0

    for live in live_statuses.values():
        total_mechanical += live.get("num_mechanical", 0)
        total_ebike += live.get("num_ebike", 0)
        total_docks_available += live.get("num_docks_available", 0)
        etat = live_state.classify_state(live)
        if etat == live_state.ETAT_VIDE:
            nb_vides += 1
        elif etat == live_state.ETAT_PLEINE:
            nb_pleines += 1

    return StatsOverview(
        nb_stations=nb_stations,
        nb_stations_avec_etat=len(live_statuses),
        total_bikes_available=total_mechanical + total_ebike,
        total_mechanical=total_mechanical,
        total_ebike=total_ebike,
        total_docks_available=total_docks_available,
        nb_stations_vides=nb_vides,
        nb_stations_pleines=nb_pleines,
    )
