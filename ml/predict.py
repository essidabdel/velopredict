"""Prédiction en direct pour une station (utilisé par l'endpoint FastAPI
GET /stations/{id}/prediction). Construit le même type de vecteur de
features que ml/features.py mais pour l'instant présent uniquement, à
partir des derniers relevés connus — pas de ré-échantillonnage sur grille
ici, juste le point le plus proche de chaque lag dans une tolérance de
30 minutes (mêmes règles que l'entraînement)."""

from __future__ import annotations

import pandas as pd
from sqlalchemy.engine import Engine

from .features import FEATURE_COLUMNS, PARIS_TZ
from .train import load_model

# Seuils du niveau de risque "vide dans 30 min", dérivés de la prédiction
# du modèle de niveau (pas une probabilité calibrée). RISK_HIGH_THRESHOLD
# reprend le seuil réglé sur validation en Phase 5ter pour le classifieur
# "régression seuillée" (voir ml/classify.py, ml/reports/RESULTATS.md §9)
# : la meilleure frontière empirique pour "sera vide". RISK_MEDIUM_THRESHOLD
# est une marge heuristique (x3) au-delà de laquelle le risque est jugé
# faible — pas calibrée formellement, affichée en niveau discret et jamais
# en probabilité brute (demande explicite de la Phase 6).
RISK_HIGH_THRESHOLD = 1.25
RISK_MEDIUM_THRESHOLD = 4.0

TOLERANCE = pd.Timedelta("30min")
LAG_OFFSETS_MINUTES = {
    "bikes_t": 0,
    "bikes_t_minus_15": 15,
    "bikes_t_minus_30": 30,
    "bikes_t_minus_60": 60,
}

_MODEL_CACHE: dict[str, object] = {}


def _cached_model(horizon: str) -> object:
    if horizon not in _MODEL_CACHE:
        _MODEL_CACHE[horizon] = load_model("lightgbm", horizon)
    return _MODEL_CACHE[horizon]


def build_live_features(engine: Engine, station_id: int) -> dict | None:
    """None si la station est inconnue, ou si les relevés récents ne
    couvrent pas les 4 lags requis (station nouvelle, flux interrompu)."""
    station = pd.read_sql(
        "SELECT capacity, lat, lon FROM stations WHERE station_id = %(station_id)s",
        engine,
        params={"station_id": station_id},
    )
    if station.empty:
        return None

    status = pd.read_sql(
        """
        SELECT ts, num_mechanical, num_ebike, num_docks_available
        FROM station_status
        WHERE station_id = %(station_id)s
        ORDER BY ts DESC
        LIMIT 50
        """,
        engine,
        params={"station_id": station_id},
        parse_dates=["ts"],
    )
    if status.empty:
        return None

    status["bikes"] = status["num_mechanical"] + status["num_ebike"]
    now = status["ts"].iloc[0]

    lags: dict[str, float] = {}
    for name, offset_minutes in LAG_OFFSETS_MINUTES.items():
        target = now - pd.Timedelta(minutes=offset_minutes)
        deltas = (status["ts"] - target).abs()
        if deltas.min() > TOLERANCE:
            return None
        lags[name] = float(status.loc[deltas.idxmin(), "bikes"])

    weather = pd.read_sql(
        "SELECT temperature_c, precipitation_mm, wind_speed_kmh FROM weather WHERE ts = %(hour)s",
        engine,
        params={"hour": now.floor("h")},
    )
    if weather.empty:
        return None

    local = now.tz_convert(PARIS_TZ)
    calendar = pd.read_sql(
        "SELECT is_public_holiday, is_school_holiday FROM calendar_days WHERE day = %(day)s",
        engine,
        params={"day": local.date()},
    )
    is_public_holiday = bool(calendar["is_public_holiday"].iloc[0]) if not calendar.empty else False
    is_school_holiday = bool(calendar["is_school_holiday"].iloc[0]) if not calendar.empty else False

    features = {
        "heure": local.hour,
        "jour_semaine": local.dayofweek,
        "is_weekend": int(local.dayofweek >= 5),
        "is_public_holiday": int(is_public_holiday),
        "is_school_holiday": int(is_school_holiday),
        "temperature_c": float(weather["temperature_c"].iloc[0]),
        "precipitation_mm": float(weather["precipitation_mm"].iloc[0]),
        "wind_speed_kmh": float(weather["wind_speed_kmh"].iloc[0]),
        **lags,
        "docks_t": float(status["num_docks_available"].iloc[0]),
        "capacity": int(station["capacity"].iloc[0]),
        "lat": float(station["lat"].iloc[0]),
        "lon": float(station["lon"].iloc[0]),
    }
    return {"as_of": now, **features}


def classify_risk_level(prediction_30min: float) -> str:
    """Niveau de risque discret "vide dans 30 min", jamais une probabilité
    brute (voir les seuils documentés plus haut)."""
    if prediction_30min <= RISK_HIGH_THRESHOLD:
        return "eleve"
    if prediction_30min <= RISK_MEDIUM_THRESHOLD:
        return "moyen"
    return "faible"


def predict_station(engine: Engine, station_id: int) -> dict | None:
    features = build_live_features(engine, station_id)
    if features is None:
        return None

    as_of = features.pop("as_of")
    X = pd.DataFrame([features])[FEATURE_COLUMNS]

    pred_30 = float(_cached_model("30").predict(X)[0])
    pred_60 = float(_cached_model("60").predict(X)[0])

    return {
        "station_id": station_id,
        "as_of": as_of.isoformat(),
        "bikes_now": features["bikes_t"],
        "prediction_30min": round(pred_30, 1),
        "prediction_60min": round(pred_60, 1),
        "risk_level_30min": classify_risk_level(pred_30),
    }
