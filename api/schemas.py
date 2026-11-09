"""Schémas Pydantic de l'API (réponses HTTP)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class StationSummary(BaseModel):
    station_id: int
    name: str
    commune_code: str | None = None
    commune_nom: str | None = None
    lat: float
    lon: float
    capacity: int
    etat: str = Field(description="vide | pleine | disponible | inconnue")
    num_mechanical: int | None = None
    num_ebike: int | None = None
    num_docks_available: int | None = None
    is_renting: bool | None = None
    is_returning: bool | None = None
    last_reported: int | None = None


class StationDetail(StationSummary):
    collected_at: str | None = None


class HistoryPoint(BaseModel):
    ts: datetime
    num_mechanical: int
    num_ebike: int
    num_docks_available: int
    is_renting: bool
    is_returning: bool


class StationPrediction(BaseModel):
    station_id: int
    as_of: str = Field(description="Horodatage des relevés utilisés pour prédire")
    bikes_now: float = Field(description="Vélos disponibles au moment de la prédiction")
    prediction_30min: float = Field(description="Vélos disponibles prédits à t+30min")
    prediction_60min: float = Field(description="Vélos disponibles prédits à t+60min")


class StatsOverview(BaseModel):
    nb_stations: int = Field(description="Nombre total de stations connues (référentiel)")
    nb_stations_avec_etat: int = Field(
        description="Nombre de stations ayant un état temps réel disponible"
    )
    total_bikes_available: int
    total_mechanical: int
    total_ebike: int
    total_docks_available: int
    nb_stations_vides: int
    nb_stations_pleines: int
