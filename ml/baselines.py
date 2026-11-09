"""Baselines de référence (CLAUDE.md) :
- persistance : la disponibilité actuelle reste la même.
- moyenne historique : moyenne par (station, heure, jour de semaine),
  apprise sur le train uniquement — jamais sur le test, pour ne pas
  fuiter d'information du futur vers l'évaluation.
"""

from __future__ import annotations

import pandas as pd

from .features import TARGET_COLUMNS


def persistence_predictions(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({target: df["bikes_t"] for target in TARGET_COLUMNS}, index=df.index)


def fit_historical_average(train_df: pd.DataFrame) -> pd.DataFrame:
    return (
        train_df.groupby(["station_id", "heure", "jour_semaine"])[TARGET_COLUMNS]
        .mean()
        .rename(columns={col: f"hist_avg_{col}" for col in TARGET_COLUMNS})
        .reset_index()
    )


def historical_average_predictions(df: pd.DataFrame, hist_avg: pd.DataFrame) -> pd.DataFrame:
    merged = df[["station_id", "heure", "jour_semaine", "bikes_t"]].merge(
        hist_avg, on=["station_id", "heure", "jour_semaine"], how="left"
    )
    result = {}
    for target in TARGET_COLUMNS:
        col = f"hist_avg_{target}"
        # repli sur la persistance si la combinaison (station, heure, jour)
        # n'a jamais été vue au train (ex: station trop récente)
        result[target] = merged[col].fillna(merged["bikes_t"]).to_numpy()
    return pd.DataFrame(result, index=df.index)
