"""Phase 5 ter, point 4 : ré-évalue le modèle sauvegardé (ml/models/) sur
nos propres données collectées en direct (`source = 'live'`, depuis le
2026-11-09), pour un test réellement indépendant — aucune de ces lignes
n'a servi à l'entraînement (qui s'est arrêté au 2026-11-01, archive
backfillée uniquement).

À relancer périodiquement : la collecte en direct est encore courte au
moment de l'écriture de ce script (quelques heures). Les métriques seront
d'autant plus fiables que la fenêtre couverte s'allonge — ce script est
prévu pour être réutilisé tel quel, sans modification, au fil des
semaines.

Usage :
    python -m ml.evaluate_live
    python -m ml.evaluate_live --start 2026-11-09 --end 2026-11-10
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime

import pandas as pd

from .config import REPORTS_DIR, get_engine
from .features import FEATURE_COLUMNS, build_feature_table
from .train import HORIZONS, load_model

logger = logging.getLogger("ml.evaluate_live")

MIN_ROWS_FOR_RELIABLE_METRICS = 1000


def resolve_live_window(engine, start: str | None, end: str | None) -> tuple[datetime, datetime]:
    if start and end:
        return (
            datetime.fromisoformat(start).replace(tzinfo=UTC),
            datetime.fromisoformat(end).replace(tzinfo=UTC),
        )
    bounds = pd.read_sql(
        "SELECT min(ts) AS debut, max(ts) AS fin FROM station_status WHERE source = 'live'", engine
    )
    if bounds["debut"].iloc[0] is None:
        raise RuntimeError("Aucune donnée 'live' en base pour le moment.")
    return bounds["debut"].iloc[0].to_pydatetime(), bounds["fin"].iloc[0].to_pydatetime()


def build_live_test_set(engine, start: datetime, end: datetime) -> pd.DataFrame:
    """Features construites uniquement sur la collecte en direct
    (source='live' explicite, jamais de mélange avec l'archive
    backfillée même si les fenêtres de temps venaient à se recouper)."""
    return build_feature_table(engine, start, end, source_filter="live")


def evaluate_live(start: str | None = None, end: str | None = None) -> pd.DataFrame | None:
    engine = get_engine()
    window_start, window_end = resolve_live_window(engine, start, end)
    logger.info("Fenêtre live évaluée : %s -> %s", window_start, window_end)

    df = build_live_test_set(engine, window_start, window_end)
    logger.info("%d lignes de features construites depuis la collecte live", len(df))

    if len(df) < MIN_ROWS_FOR_RELIABLE_METRICS:
        logger.warning(
            "Seulement %d lignes disponibles (< %d) : collecte live encore trop courte pour "
            "des métriques fiables. Résultat affiché quand même, à titre indicatif uniquement "
            "— relancer ce script dans quelques jours pour un vrai test indépendant.",
            len(df),
            MIN_ROWS_FOR_RELIABLE_METRICS,
        )

    # Import tardif : voir ml/retrain.py et ml/reports/RESULTATS.md pour
    # l'explication (sklearn.metrics/matplotlib avant un .fit() LightGBM
    # fait planter le process sur cette machine). Ici on ne fait QUE de
    # l'inférence (predict), donc l'ordre importe moins, mais on garde la
    # même discipline pour rester cohérent et sans risque.
    from .baselines import persistence_predictions
    from .evaluate import compute_metrics

    persistence_pred = persistence_predictions(df)

    rows = []
    for horizon, target in HORIZONS.items():
        y_true = df[target]
        model = load_model("lightgbm", horizon)
        y_pred_model = model.predict(df[FEATURE_COLUMNS])
        rows.append(
            {
                "horizon": horizon,
                "modele": "persistance",
                "nb_lignes": len(df),
                **compute_metrics(y_true, persistence_pred[target]),
            }
        )
        rows.append(
            {
                "horizon": horizon,
                "modele": "lightgbm",
                "nb_lignes": len(df),
                **compute_metrics(y_true, y_pred_model),
            }
        )

    metrics = pd.DataFrame(rows)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / "metriques_live.csv"
    metrics.to_csv(out_path, index=False)
    logger.info("Métriques live enregistrées dans %s", out_path)
    logger.info("\n%s", metrics.to_string(index=False))
    return metrics


def main() -> None:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", help="Début de la fenêtre (ISO 8601)")
    parser.add_argument("--end", help="Fin de la fenêtre (ISO 8601)")
    args = parser.parse_args()
    evaluate_live(start=args.start, end=args.end)


if __name__ == "__main__":
    main()
