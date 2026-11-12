"""DAG déclenché manuellement : rafraîchit le référentiel des stations
(nom, capacité, coordonnées) puis leur commune/arrondissement.

Depuis l'ajout de `rafraichir_stations` à `enrichissement_quotidien.py`
(DAG planifié chaque nuit), le référentiel de base (nom/capacité/
coordonnées) est déjà à jour quotidiennement — une nouvelle station
apparaît sur la carte dès le lendemain de son ouverture. `charger_stations`
reste ici par simplicité/robustesse (upsert idempotent, sans effet si déjà
à jour) : ce DAG sert surtout à lancer `ingestion.stations_geo`, le plus
lent des trois DAGs (reverse-geocoding via geo.api.gouv.fr, ~6-8 min la
première fois) — pas automatisé chaque nuit car la position d'une station
ne change jamais une fois créée, inutile de le revérifier en continu. À
déclencher à la main depuis l'UI Airflow quand on sait qu'une nouvelle
station doit recevoir sa commune/arrondissement.
"""

from __future__ import annotations

import datetime

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/opt/project"

with DAG(
    dag_id="maj_referentiel_stations",
    description=(
        "Rafraîchit le référentiel des stations (nom, capacité, coordonnées, "
        "commune/arrondissement) — déclenchement manuel"
    ),
    schedule=None,
    start_date=datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC),
    catchup=False,
    tags=["velopredict", "referentiel"],
) as dag:
    charger_stations = BashOperator(
        task_id="charger_stations",
        bash_command=f"cd {PROJECT_DIR} && python -m ingestion.stations",
    )

    geocoder_stations = BashOperator(
        task_id="geocoder_stations",
        bash_command=f"cd {PROJECT_DIR} && python -m ingestion.stations_geo",
    )

    # Le géocodage a besoin du référentiel à jour : séquentiel.
    charger_stations >> geocoder_stations
