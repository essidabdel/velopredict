"""Exporte les vues d'agrégation (database/migrations/003_analysis_views.sql)
en CSV propres, prêts à être ouverts dans Power BI (ou Excel). Rejouable
sans risque : chaque export écrase simplement le fichier précédent.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from _common import get_engine

EXPORT_DIR = Path(__file__).resolve().parent / "exports"

VIEWS = {
    "disponibilite_horaire.csv": "SELECT * FROM v_hourly_availability ORDER BY jour_type, heure",
    "flux_domicile_travail.csv": (
        "SELECT * FROM v_station_flux_domicile_travail ORDER BY station_id"
    ),
    "mouvement_meteo_horaire.csv": "SELECT * FROM v_hourly_movement_weather ORDER BY heure",
    "repartition_velos.csv": "SELECT * FROM v_bike_type_share ORDER BY heure",
    "penurie_par_commune.csv": "SELECT * FROM v_penurie_par_commune ORDER BY taux_penurie DESC",
}


def export_all() -> None:
    EXPORT_DIR.mkdir(exist_ok=True)
    engine = get_engine()
    for filename, sql in VIEWS.items():
        df = pd.read_sql(sql, engine)
        path = EXPORT_DIR / filename
        df.to_csv(path, index=False, encoding="utf-8")
        print(f"{filename} : {len(df)} lignes -> {path}")


if __name__ == "__main__":
    export_all()
