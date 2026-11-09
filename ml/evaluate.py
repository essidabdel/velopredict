"""Évaluation des modèles : MAE/RMSE par horizon comparées aux baselines,
graphes matplotlib (réel vs prédit, erreur par heure, importance SHAP)
enregistrés dans ml/reports/."""

from __future__ import annotations

import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .baselines import (
    fit_historical_average,
    historical_average_predictions,
    persistence_predictions,
)
from .config import REPORTS_DIR
from .features import FEATURE_COLUMNS
from .train import HORIZONS

logger = logging.getLogger("ml.evaluate")

SHAP_SAMPLE_SIZE = 2000
SCATTER_SAMPLE_SIZE = 5000


def compute_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(mean_squared_error(y_true, y_pred) ** 0.5),
    }


def evaluate_all(
    train: pd.DataFrame, test: pd.DataFrame, models: dict[str, dict[str, object]]
) -> tuple[pd.DataFrame, dict[str, dict[str, np.ndarray]]]:
    """Retourne (tableau de métriques, prédictions par horizon/modèle) —
    les prédictions sont réutilisées ensuite pour les graphiques."""
    hist_avg = fit_historical_average(train)
    persistence_pred = persistence_predictions(test)
    hist_pred = historical_average_predictions(test, hist_avg)

    rows = []
    predictions: dict[str, dict[str, np.ndarray]] = {}
    for horizon, target in HORIZONS.items():
        y_true = test[target]
        predictions[horizon] = {
            "persistance": persistence_pred[target].to_numpy(),
            "moyenne_historique": hist_pred[target].to_numpy(),
        }
        for name, model in models[horizon].items():
            predictions[horizon][name] = np.asarray(model.predict(test[FEATURE_COLUMNS]))

        for modele, y_pred in predictions[horizon].items():
            rows.append({"horizon": horizon, "modele": modele, **compute_metrics(y_true, y_pred)})

    return pd.DataFrame(rows), predictions


def evaluate_changing_subset(
    test: pd.DataFrame, predictions: dict[str, dict[str, np.ndarray]]
) -> pd.DataFrame:
    """MAE restreinte aux lignes où la disponibilité a réellement changé
    entre t et t+horizon (bikes_t_plus_h != bikes_t). Sur ce sous-
    ensemble, la persistance ne peut plus "gagner par défaut" en ne
    bougeant jamais : ça isole la vraie capacité des modèles à capter la
    dynamique plutôt que la simple stabilité du signal."""
    rows = []
    for horizon, target in HORIZONS.items():
        changing = test[target] != test["bikes_t"]
        nb_changing = int(changing.sum())
        y_true = test.loc[changing, target]
        for modele, y_pred in predictions[horizon].items():
            y_pred_changing = np.asarray(y_pred)[changing.to_numpy()]
            rows.append(
                {
                    "horizon": horizon,
                    "modele": modele,
                    "nb_lignes_qui_changent": nb_changing,
                    "part_lignes_qui_changent": nb_changing / len(test),
                    **compute_metrics(y_true, y_pred_changing),
                }
            )
    return pd.DataFrame(rows)


def plot_real_vs_predicted(
    test: pd.DataFrame, predictions: dict[str, np.ndarray], horizon: str
) -> None:
    target = HORIZONS[horizon]
    y_true = test[target].to_numpy()
    y_pred = predictions["lightgbm"]

    rng = np.random.RandomState(42)
    sample_size = min(SCATTER_SAMPLE_SIZE, len(y_true))
    idx = rng.choice(len(y_true), sample_size, replace=False)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(y_true[idx], y_pred[idx], alpha=0.15, s=8)
    lims = [0, max(y_true.max(), y_pred.max())]
    ax.plot(
        lims, lims, color="red", linestyle="--", linewidth=1, label="y = x (prédiction parfaite)"
    )
    ax.set_xlabel("Réel (vélos disponibles)")
    ax.set_ylabel("Prédit (LightGBM)")
    ax.set_title(f"Réel vs prédit — horizon t+{horizon}min")
    ax.legend()
    plt.tight_layout()
    fig.savefig(REPORTS_DIR / f"reel_vs_predit_{horizon}min.png", dpi=120)
    plt.close(fig)


def plot_error_by_hour(
    test: pd.DataFrame, predictions: dict[str, np.ndarray], horizon: str
) -> None:
    target = HORIZONS[horizon]
    tmp = test[["heure"]].copy()
    model_names = list(predictions.keys())
    for name in model_names:
        tmp[name] = (test[target] - predictions[name]).abs()
    grouped = tmp.groupby("heure")[model_names].mean()

    fig, ax = plt.subplots(figsize=(9, 5))
    # persistance et lightgbm mis en avant (trait plus épais), c'est la
    # comparaison demandée ; les autres modèles restent visibles en fond.
    for name in grouped.columns:
        emphase = name in ("persistance", "lightgbm")
        ax.plot(
            grouped.index,
            grouped[name],
            marker="o",
            label=name,
            linewidth=2.5 if emphase else 1.2,
            alpha=1.0 if emphase else 0.6,
        )
    ax.set_xlabel("Heure (Europe/Paris)")
    ax.set_ylabel("MAE (vélos)")
    ax.set_title(f"Erreur moyenne par heure de la journée — horizon t+{horizon}min")
    ax.set_xticks(range(0, 24))
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig(REPORTS_DIR / f"erreur_par_heure_{horizon}min.png", dpi=120)
    plt.close(fig)


def plot_shap_importance(model: object, test: pd.DataFrame, horizon: str) -> None:
    # Import local (pas en tête de module) : charger `shap` avant
    # d'entraîner LightGBM provoque un crash natif (violation d'accès
    # mémoire) sur cette machine, probablement un conflit entre runtimes
    # OpenMP de différentes bibliothèques compilées. En l'important ici,
    # l'entraînement est déjà terminé quand shap se charge.
    import shap

    sample = test[FEATURE_COLUMNS].sample(n=min(SHAP_SAMPLE_SIZE, len(test)), random_state=42)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(sample)

    plt.figure(figsize=(8, 6))
    shap.summary_plot(shap_values, sample, show=False, plot_type="bar")
    plt.title(f"Importance des variables (SHAP) — horizon t+{horizon}min")
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / f"shap_importance_{horizon}min.png", dpi=120)
    plt.close()


def generate_all_plots(
    test: pd.DataFrame,
    predictions: dict[str, dict[str, np.ndarray]],
    models: dict[str, dict[str, object]],
) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for horizon in HORIZONS:
        plot_real_vs_predicted(test, predictions[horizon], horizon)
        plot_error_by_hour(test, predictions[horizon], horizon)
        plot_shap_importance(models[horizon]["lightgbm"], test, horizon)
        logger.info("Graphiques générés pour l'horizon t+%smin", horizon)
