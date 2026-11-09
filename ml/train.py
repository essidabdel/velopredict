"""Entraînement des modèles : découpage temporel uniquement (jamais
aléatoire, cf CLAUDE.md), régression linéaire puis LightGBM, un modèle
par horizon (t+30, t+60).

La régression linéaire est entraînée dans un sous-process isolé (voir
ml/_train_linear_worker.py) : l'entraîner dans le même process que
LightGBM provoque un crash natif reproductible sur cette machine.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import joblib
import pandas as pd
from lightgbm import LGBMRegressor

from .config import MODELS_DIR
from .features import FEATURE_COLUMNS

HORIZONS = {"30": "bikes_t_plus_30", "60": "bikes_t_plus_60"}
MODEL_NAMES = ("linear_regression", "lightgbm", "lightgbm_delta")
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DeltaLightGBM:
    """Enveloppe un LGBMRegressor entraîné sur la variation
    y(t+h) - y(t) plutôt que sur le niveau : .predict() reconstruit
    directement le niveau prédit (bikes_t + delta prédit), pour rester
    directement comparable aux autres modèles (mêmes MAE/RMSE en niveau)."""

    def __init__(self, delta_model: LGBMRegressor):
        self.delta_model = delta_model

    def predict(self, X: pd.DataFrame):
        delta = self.delta_model.predict(X)
        return X["bikes_t"].to_numpy() + delta


def temporal_split(
    df: pd.DataFrame, test_fraction: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Découpage temporel strict : les dernières lignes par ordre
    chronologique vont au test, jamais de split aléatoire (sinon fuite de
    données). Toutes les lignes partageant le même horodatage (une par
    station) restent du même côté de la coupure."""
    df_sorted = df.sort_values("ts").reset_index(drop=True)
    cutoff_idx = int(len(df_sorted) * (1 - test_fraction))
    cutoff_ts = df_sorted.loc[cutoff_idx, "ts"]
    train = df_sorted[df_sorted["ts"] < cutoff_ts].reset_index(drop=True)
    test = df_sorted[df_sorted["ts"] >= cutoff_ts].reset_index(drop=True)
    return train, test


def train_lightgbm(train: pd.DataFrame, target: str) -> LGBMRegressor:
    model = LGBMRegressor(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=50,
        random_state=42,
        verbosity=-1,
        # n_jobs=1 : le multi-threading natif de LightGBM provoque une
        # violation d'accès mémoire sur cette machine Windows (reproduit
        # et isolé manuellement — fonctionne à l'identique en mono-thread,
        # juste plus lent). Un run sur une autre machine pourra retirer
        # cette contrainte.
        n_jobs=1,
    )
    model.fit(train[FEATURE_COLUMNS], train[target])
    return model


def train_lightgbm_delta(train: pd.DataFrame, target: str) -> DeltaLightGBM:
    """Même LightGBM, mais entraîné à prédire la variation
    (y(t+h) - bikes_t) plutôt que le niveau absolu — hypothèse : plus
    facile d'apprendre "de combien ça va changer" que "quelle sera la
    valeur", surtout avec bikes_t déjà dominant dans les features."""
    delta_target = train[target] - train["bikes_t"]
    model = LGBMRegressor(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=50,
        random_state=42,
        verbosity=-1,
        n_jobs=1,  # voir la note dans train_lightgbm
    )
    model.fit(train[FEATURE_COLUMNS], delta_target)
    return DeltaLightGBM(model)


def train_linear_regression_isolated(train: pd.DataFrame, target: str, output_path: Path) -> None:
    """Entraîne via ml/_train_linear_worker.py dans un sous-process isolé
    (voir ce module pour l'explication du crash que ça contourne)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "train.parquet"
        train[[*FEATURE_COLUMNS, target]].to_parquet(tmp_path)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "ml._train_linear_worker",
                "--train-path",
                str(tmp_path),
                "--target",
                target,
                "--output-path",
                str(output_path),
            ],
            check=True,
            cwd=PROJECT_ROOT,
        )


def train_all(train: pd.DataFrame) -> dict[str, dict[str, object]]:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    models: dict[str, dict[str, object]] = {horizon: {} for horizon in HORIZONS}

    for horizon, target in HORIZONS.items():
        models[horizon]["lightgbm"] = train_lightgbm(train, target)
        models[horizon]["lightgbm_delta"] = train_lightgbm_delta(train, target)

    for horizon, target in HORIZONS.items():
        output_path = MODELS_DIR / f"linear_regression_{horizon}.joblib"
        train_linear_regression_isolated(train, target, output_path)
        models[horizon]["linear_regression"] = joblib.load(output_path)

    return models


def save_models(models: dict[str, dict[str, object]]) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for horizon, by_model in models.items():
        for name, model in by_model.items():
            joblib.dump(model, MODELS_DIR / f"{name}_{horizon}.joblib")


def load_model(name: str, horizon: str) -> object:
    return joblib.load(MODELS_DIR / f"{name}_{horizon}.joblib")


def load_all_models() -> dict[str, dict[str, object]]:
    return {
        horizon: {name: load_model(name, horizon) for name in MODEL_NAMES} for horizon in HORIZONS
    }
