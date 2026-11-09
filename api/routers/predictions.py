"""Endpoint de prédiction : réutilise directement ml/predict.py (modèle
LightGBM entraîné par ml/retrain.py, chargé depuis ml/models/)."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Engine

from ml.config import get_engine
from ml.predict import predict_station
from ml.train import MODELS_DIR

from ..schemas import StationPrediction

router = APIRouter(tags=["predictions"])


@lru_cache(maxsize=1)
def get_ml_engine() -> Engine:
    return get_engine()


@router.get("/stations/{station_id}/prediction", response_model=StationPrediction)
def get_station_prediction(
    station_id: int,
    engine: Annotated[Engine, Depends(get_ml_engine)],
):
    if not (MODELS_DIR / "lightgbm_30.joblib").exists():
        raise HTTPException(
            status_code=503,
            detail="Modèle non entraîné — lancer `python -m ml.retrain` au préalable.",
        )

    result = predict_station(engine, station_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Station inconnue, ou historique récent insuffisant pour prédire "
            "(besoin des relevés t, t-15, t-30 et t-60 dans une tolérance de 30 min).",
        )
    return StationPrediction(**result)
