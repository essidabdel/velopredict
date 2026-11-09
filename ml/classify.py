"""Phase 5 ter : classification binaire "station vide à t+30min", avec
gestion du déséquilibre de classes et réglage du seuil de décision sur
une validation temporelle — jamais sur le test.

Découpage à trois niveaux, strictement temporel (jamais aléatoire) :
    train_fit -> entraînement (classifieur + régression dédiée à cette
                 comparaison, refaite sur train_fit pour une comparaison
                 équitable avec le classifieur, lui aussi entraîné sur
                 train_fit)
    val       -> réglage du seuil de décision (jamais vu à l'entraînement)
    test      -> évaluation finale (le même test que ml/retrain.py)

val est prélevée à la fin de `train` (le même train que ml/retrain.py
utiliserait seul), donc train_fit < val < test, sans chevauchement.

Import note : comme ml/evaluate.py, ce module importe sklearn.metrics
localement (dans les fonctions, pas en tête de fichier) : l'importer
avant un .fit() LightGBM fait planter le process sur cette machine
(conflit de runtimes natifs, voir ml/train.py et ml/reports/RESULTATS.md).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier

from .features import FEATURE_COLUMNS
from .train import HORIZONS, temporal_split, train_lightgbm

logger = logging.getLogger("ml.classify")

CLASSIFIER_THRESHOLDS = np.linspace(0.01, 0.99, 99)
REGRESSION_THRESHOLDS = np.arange(0.0, 10.25, 0.25)


def three_way_split(
    df: pd.DataFrame, test_fraction: float = 0.2, val_fraction: float = 0.15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """train_fit / val / test, tous strictement chronologiques et
    disjoints (jamais de split aléatoire)."""
    train, test = temporal_split(df, test_fraction=test_fraction)
    train_fit, val = temporal_split(train, test_fraction=val_fraction)
    return train_fit, val, test


def train_empty_classifier(train_fit: pd.DataFrame, target: str) -> LGBMClassifier:
    """LightGBM binaire, scale_pos_weight calculé depuis le déséquilibre
    réel du train_fit (nb stations pleines/non-vides vs vides)."""
    y = (train_fit[target] == 0).astype(int)
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    scale_pos_weight = n_neg / n_pos
    logger.info(
        "Classifieur 'vide' : %d positifs / %d negatifs dans train_fit (scale_pos_weight=%.1f)",
        n_pos,
        n_neg,
        scale_pos_weight,
    )
    model = LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=50,
        random_state=42,
        verbosity=-1,
        n_jobs=1,  # voir la note dans ml/train.py::train_lightgbm
        scale_pos_weight=scale_pos_weight,
    )
    model.fit(train_fit[FEATURE_COLUMNS], y)
    return model


def tune_threshold(
    y_true: np.ndarray, scores: np.ndarray, candidates: np.ndarray, direction: str
) -> tuple[float, float]:
    """Seuil qui maximise le F1. direction='ge' : positif si
    scores >= seuil (proba d'un classifieur) ; direction='le' : positif
    si scores <= seuil (niveau prédit par une régression — plus c'est
    bas, plus "vide" est probable)."""
    from sklearn.metrics import f1_score  # import local, voir note en tête de module

    best_threshold, best_f1 = float(candidates[0]), -1.0
    for threshold in candidates:
        y_pred = (scores >= threshold) if direction == "ge" else (scores <= threshold)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        if f1 > best_f1:
            best_f1, best_threshold = f1, float(threshold)
    return best_threshold, best_f1


def persistence_empty_prediction(df: pd.DataFrame) -> np.ndarray:
    """Prédiction "vide" par persistance : vide maintenant => vide plus
    tard. Toujours False quand bikes_t > 0, par construction."""
    return (df["bikes_t"] == 0).to_numpy()


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import f1_score, precision_score, recall_score  # import local

    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "rappel": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def run_empty_classification_experiment(df: pd.DataFrame, horizon: str = "30") -> dict[str, object]:
    """Pipeline complet : split à 3 niveaux, entraînement classifieur +
    régression dédiée (toutes deux sur train_fit), réglage de seuil sur
    val, évaluation sur test — classification "vide" pleine, puis
    restreinte à l'événement "devient vide" (bikes_t > 0)."""
    target = HORIZONS[horizon]
    train_fit, val, test = three_way_split(df)
    logger.info(
        "Split classification (horizon t+%smin) :\n"
        "  train_fit : %d lignes, du %s au %s\n"
        "  val       : %d lignes, du %s au %s\n"
        "  test      : %d lignes, du %s au %s",
        horizon,
        len(train_fit),
        train_fit["ts"].min(),
        train_fit["ts"].max(),
        len(val),
        val["ts"].min(),
        val["ts"].max(),
        len(test),
        test["ts"].min(),
        test["ts"].max(),
    )

    classifier = train_empty_classifier(train_fit, target)
    regression = train_lightgbm(train_fit, target)

    y_val = (val[target] == 0).to_numpy()
    clf_val_scores = classifier.predict_proba(val[FEATURE_COLUMNS])[:, 1]
    reg_val_scores = regression.predict(val[FEATURE_COLUMNS])

    clf_threshold, clf_val_f1 = tune_threshold(y_val, clf_val_scores, CLASSIFIER_THRESHOLDS, "ge")
    reg_threshold, reg_val_f1 = tune_threshold(y_val, reg_val_scores, REGRESSION_THRESHOLDS, "le")
    logger.info(
        "Seuils regles sur validation : classifieur proba>=%.2f (F1 val=%.3f), "
        "regression seuillee niveau<=%.2f (F1 val=%.3f)",
        clf_threshold,
        clf_val_f1,
        reg_threshold,
        reg_val_f1,
    )

    y_test = (test[target] == 0).to_numpy()
    clf_test_scores = classifier.predict_proba(test[FEATURE_COLUMNS])[:, 1]
    reg_test_scores = regression.predict(test[FEATURE_COLUMNS])

    predictions = {
        "classifieur_lightgbm": clf_test_scores >= clf_threshold,
        "regression_seuillee": reg_test_scores <= reg_threshold,
        "persistance": persistence_empty_prediction(test),
    }

    empty_rows = [
        {"modele": name, "nb_lignes": len(y_test), **classification_metrics(y_test, y_pred)}
        for name, y_pred in predictions.items()
    ]
    empty_metrics = pd.DataFrame(empty_rows)

    # Événement "devient vide" : bikes_t > 0 et cible == 0, restreint au
    # sous-ensemble bikes_t > 0 (sinon "devenir vide" n'a pas de sens).
    becomes_empty_mask = (test["bikes_t"] > 0).to_numpy()
    y_test_becomes = y_test[becomes_empty_mask]
    becomes_rows = []
    for name, y_pred in predictions.items():
        y_pred_becomes = y_pred[becomes_empty_mask]
        becomes_rows.append(
            {
                "modele": name,
                "nb_lignes": int(becomes_empty_mask.sum()),
                "nb_devient_vide_reel": int(y_test_becomes.sum()),
                **classification_metrics(y_test_becomes, y_pred_becomes),
            }
        )
    becomes_empty_metrics = pd.DataFrame(becomes_rows)

    return {
        "classifier": classifier,
        "regression": regression,
        "clf_threshold": clf_threshold,
        "reg_threshold": reg_threshold,
        "clf_val_f1": clf_val_f1,
        "reg_val_f1": reg_val_f1,
        "train_fit_range": (train_fit["ts"].min(), train_fit["ts"].max()),
        "val_range": (val["ts"].min(), val["ts"].max()),
        "empty_metrics": empty_metrics,
        "becomes_empty_metrics": becomes_empty_metrics,
    }
