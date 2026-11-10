"""Endpoints stations : liste filtrée, détail, historique."""

from __future__ import annotations

from typing import Annotated, Literal

import psycopg2.extensions
import redis
from fastapi import APIRouter, Depends, HTTPException, Query

from .. import live_state
from ..db import get_db
from ..redis_client import get_redis
from ..schemas import HistoryPoint, StationDetail, StationSummary

router = APIRouter(tags=["stations"])

VeloType = Literal["mecanique", "electrique"]
EtatType = Literal["vide", "faible", "pleine", "disponible"]


def _build_summary(row: dict, live: dict | None) -> StationSummary:
    return StationSummary(
        station_id=row["station_id"],
        name=row["name"],
        commune_code=row.get("commune_code"),
        commune_nom=row.get("commune_nom"),
        lat=row["lat"],
        lon=row["lon"],
        capacity=row["capacity"],
        etat=live_state.classify_state(live, row["capacity"]),
        num_mechanical=live.get("num_mechanical") if live else None,
        num_ebike=live.get("num_ebike") if live else None,
        num_docks_available=live.get("num_docks_available") if live else None,
        is_renting=live.get("is_renting") if live else None,
        is_returning=live.get("is_returning") if live else None,
        last_reported=live.get("last_reported") if live else None,
    )


def _station_has_velo_type(live: dict | None, velo: VeloType) -> bool:
    if live is None:
        return False
    field = "num_mechanical" if velo == "mecanique" else "num_ebike"
    return live.get(field, 0) > 0


@router.get("/stations", response_model=list[StationSummary])
def list_stations(
    conn: Annotated[psycopg2.extensions.connection, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    arrondissement: Annotated[
        str | None,
        Query(
            description="Filtre sur la commune/l'arrondissement (recherche partielle, ex: '16e')"
        ),
    ] = None,
    velo: Annotated[
        VeloType | None,
        Query(description="Ne garder que les stations avec au moins un vélo de ce type"),
    ] = None,
    etat: Annotated[
        EtatType | None,
        Query(description="Ne garder que les stations dans cet état"),
    ] = None,
    recherche: Annotated[
        str | None,
        Query(description="Recherche partielle sur le nom de la station"),
    ] = None,
):
    sql = "SELECT station_id, name, commune_code, commune_nom, lat, lon, capacity FROM stations"
    conditions = []
    params: dict[str, str] = {}
    if arrondissement:
        conditions.append("commune_nom ILIKE %(arrondissement)s")
        params["arrondissement"] = f"%{arrondissement}%"
    if recherche:
        conditions.append("name ILIKE %(recherche)s")
        params["recherche"] = f"%{recherche}%"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY station_id"

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    station_ids = [row["station_id"] for row in rows]
    live_statuses = live_state.fetch_live_statuses(redis_client, station_ids)

    results = []
    for row in rows:
        live = live_statuses.get(row["station_id"])
        if velo is not None and not _station_has_velo_type(live, velo):
            continue
        if etat is not None and live_state.classify_state(live, row["capacity"]) != etat:
            continue
        results.append(_build_summary(row, live))
    return results


@router.get("/stations/{station_id}", response_model=StationDetail)
def get_station(
    station_id: int,
    conn: Annotated[psycopg2.extensions.connection, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT station_id, name, commune_code, commune_nom, lat, lon, capacity "
            "FROM stations WHERE station_id = %(station_id)s",
            {"station_id": station_id},
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Station inconnue")

    live = live_state.fetch_live_statuses(redis_client, [station_id]).get(station_id)
    summary = _build_summary(row, live)
    return StationDetail(
        **summary.model_dump(), collected_at=live.get("collected_at") if live else None
    )


@router.get("/stations/{station_id}/history", response_model=list[HistoryPoint])
def get_station_history(
    station_id: int,
    conn: Annotated[psycopg2.extensions.connection, Depends(get_db)],
    hours: Annotated[int, Query(ge=1, le=168, description="Fenêtre d'historique en heures")] = 24,
):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM stations WHERE station_id = %(station_id)s", {"station_id": station_id}
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Station inconnue")

        cur.execute(
            "SELECT ts, num_mechanical, num_ebike, num_docks_available, is_renting, is_returning "
            "FROM station_status "
            "WHERE station_id = %(station_id)s AND ts > now() - (%(hours)s || ' hours')::interval "
            "ORDER BY ts",
            {"station_id": station_id, "hours": hours},
        )
        rows = cur.fetchall()
    return [HistoryPoint(**row) for row in rows]
