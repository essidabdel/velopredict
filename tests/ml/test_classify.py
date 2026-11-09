import numpy as np
import pandas as pd

from ml.classify import classification_metrics, persistence_empty_prediction, tune_threshold


def test_persistence_empty_prediction_matches_current_bikes():
    df = pd.DataFrame({"bikes_t": [0, 5, 0, 12]})
    result = persistence_empty_prediction(df)
    assert list(result) == [True, False, True, False]


def test_classification_metrics_known_values():
    y_true = np.array([True, True, False, False])
    y_pred = np.array([True, False, True, False])
    # TP=1, FP=1, FN=1, TN=1 -> precision=0.5, rappel=0.5, f1=0.5
    metrics = classification_metrics(y_true, y_pred)
    assert metrics["precision"] == 0.5
    assert metrics["rappel"] == 0.5
    assert metrics["f1"] == 0.5


def test_classification_metrics_zero_division_safe():
    y_true = np.array([False, False, False])
    y_pred = np.array([False, False, False])
    metrics = classification_metrics(y_true, y_pred)
    assert metrics == {"precision": 0.0, "rappel": 0.0, "f1": 0.0}


def test_tune_threshold_ge_finds_optimal_cut():
    # Separation nette : positifs ont un score >= 0.7, negatifs <= 0.3
    y_true = np.array([True, True, True, False, False, False])
    scores = np.array([0.9, 0.8, 0.7, 0.3, 0.2, 0.1])
    candidates = np.linspace(0.1, 0.9, 9)

    threshold, f1 = tune_threshold(y_true, scores, candidates, "ge")

    assert 0.3 < threshold <= 0.7
    assert f1 == 1.0


def test_tune_threshold_le_finds_optimal_cut():
    # "positif" si score <= seuil (cas regression seuillee)
    y_true = np.array([True, True, False, False])
    scores = np.array([0.5, 1.0, 5.0, 6.0])
    candidates = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])

    threshold, f1 = tune_threshold(y_true, scores, candidates, "le")

    assert 1.0 <= threshold < 5.0
    assert f1 == 1.0
