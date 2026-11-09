"""Script de réentraînement, de bout en bout et réutilisable :
features → découpage temporel → entraînement → évaluation → sauvegarde.

Par défaut, utilise toute la fenêtre disponible dans
`v_training_eligible_status` (voir ingestion/backfill.py). À relancer
périodiquement (manuellement, ou via Airflow plus tard) à mesure que la
collecte en direct accumule des jours supplémentaires.

Usage :
    python -m ml.retrain
    python -m ml.retrain --start 2026-10-05 --end 2026-11-02 --test-fraction 0.2
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime

import pandas as pd

from .config import REPORTS_DIR, get_engine
from .features import build_feature_table
from .train import save_models, temporal_split, train_all

# NB : ml.evaluate importe matplotlib et sklearn.metrics. Importer ces
# bibliothèques AVANT d'entraîner LightGBM fait planter le process sur
# cette machine Windows (violation d'accès mémoire native, reproduit et
# isolé manuellement — un pur conflit d'ordre de chargement de DLL, pas
# un bug d'exécution). On importe donc ml.evaluate seulement après
# train_all(), à l'intérieur de run().

logger = logging.getLogger("ml.retrain")


def resolve_window(engine, start: str | None, end: str | None) -> tuple[datetime, datetime]:
    if start and end:
        return (
            datetime.fromisoformat(start).replace(tzinfo=UTC),
            datetime.fromisoformat(end).replace(tzinfo=UTC),
        )
    bounds = pd.read_sql(
        "SELECT min(ts) AS debut, max(ts) AS fin FROM v_training_eligible_status", engine
    )
    debut = bounds["debut"].iloc[0].to_pydatetime()
    fin = bounds["fin"].iloc[0].to_pydatetime()
    return debut, fin


def run(
    start: str | None = None, end: str | None = None, test_fraction: float = 0.2
) -> pd.DataFrame:
    engine = get_engine()

    window_start, window_end = resolve_window(engine, start, end)
    logger.info("Fenêtre d'entraînement : %s -> %s", window_start, window_end)

    logger.info("Construction des features...")
    df = build_feature_table(engine, window_start, window_end)
    logger.info("%d lignes de features construites", len(df))

    train, test = temporal_split(df, test_fraction=test_fraction)
    logger.info(
        "Decoupage temporel (strict, jamais aleatoire) :\n"
        "  TRAIN : %d lignes, du %s au %s\n"
        "  TEST  : %d lignes, du %s au %s",
        len(train),
        train["ts"].min(),
        train["ts"].max(),
        len(test),
        test["ts"].min(),
        test["ts"].max(),
    )

    logger.info("Entraînement des modèles (régression linéaire, LightGBM)...")
    models = train_all(train)
    save_models(models)
    logger.info("Modèles sauvegardés dans ml/models/")

    logger.info("Classification 'station vide' (seuil réglé sur validation)...")
    # Import tardif pour la même raison que ml.evaluate (voir note en tête
    # de fichier) : ml.classify entraîne encore du LightGBM (classifieur +
    # régression dédiée) après ce point, donc doit passer avant le premier
    # import de sklearn.metrics/matplotlib dans ce process.
    from .classify import run_empty_classification_experiment

    classification_results = run_empty_classification_experiment(df, horizon="30")
    empty_path = REPORTS_DIR / "classification_station_vide_30min.csv"
    becomes_empty_path = REPORTS_DIR / "classification_devient_vide_30min.csv"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    classification_results["empty_metrics"].to_csv(empty_path, index=False)
    classification_results["becomes_empty_metrics"].to_csv(becomes_empty_path, index=False)
    logger.info("Classification 'vide' enregistrée dans %s et %s", empty_path, becomes_empty_path)
    logger.info(
        "Vide (ensemble du test) :\n%s",
        classification_results["empty_metrics"].to_string(index=False),
    )
    logger.info(
        "Devient vide (bikes_t > 0 -> cible == 0) :\n%s",
        classification_results["becomes_empty_metrics"].to_string(index=False),
    )

    logger.info("Évaluation (baselines incluses)...")
    from .evaluate import (  # import tardif, voir note en tête de fichier
        evaluate_all,
        evaluate_changing_subset,
        generate_all_plots,
    )

    metrics, predictions = evaluate_all(train, test, models)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = REPORTS_DIR / "metriques.csv"
    metrics.to_csv(metrics_path, index=False)
    logger.info("Métriques enregistrées dans %s", metrics_path)
    logger.info("\n%s", metrics.to_string(index=False))

    changing_metrics = evaluate_changing_subset(test, predictions)
    changing_path = REPORTS_DIR / "metriques_stations_qui_changent.csv"
    changing_metrics.to_csv(changing_path, index=False)
    logger.info("MAE sur les lignes qui changent enregistrée dans %s", changing_path)
    logger.info("\n%s", changing_metrics.to_string(index=False))

    logger.info("Génération des graphiques...")
    generate_all_plots(test, predictions, models)
    logger.info("Graphiques enregistrés dans ml/reports/")

    logger.info(
        "Second jeu de test : 2026-11-02 / 2026-11-03 (exclus de la fenêtre principale, "
        "voir ml/reports/RESULTATS.md pour la justification)..."
    )
    nov23_df = build_feature_table(
        engine,
        datetime(2026, 11, 2, tzinfo=UTC),
        datetime(2026, 11, 4, tzinfo=UTC),
        include_unreliable=True,
    )
    logger.info("%d lignes de features pour le 2-3 novembre", len(nov23_df))
    if len(nov23_df) > 0:
        nov23_metrics, _ = evaluate_all(train, nov23_df, models)
        nov23_path = REPORTS_DIR / "metriques_test_2_3_novembre.csv"
        nov23_metrics.to_csv(nov23_path, index=False)
        logger.info("Métriques du 2-3 novembre enregistrées dans %s", nov23_path)
        logger.info("\n%s", nov23_metrics.to_string(index=False))
    else:
        logger.warning("Aucune ligne exploitable pour le 2-3 novembre, second test set ignoré")

    return metrics


def main() -> None:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", help="Début de la fenêtre (ISO 8601), ex: 2026-10-05")
    parser.add_argument("--end", help="Fin de la fenêtre (ISO 8601), ex: 2026-11-02")
    parser.add_argument(
        "--test-fraction",
        type=float,
        default=0.2,
        help="Fraction (chronologique) des données réservée au test (défaut: 0.2)",
    )
    args = parser.parse_args()
    run(start=args.start, end=args.end, test_fraction=args.test_fraction)


if __name__ == "__main__":
    main()
