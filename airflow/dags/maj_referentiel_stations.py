"""DAG déclenché manuellement : rafraîchit le référentiel des stations
(nom, capacité, coordonnées) puis leur commune/arrondissement.

Ne tourne jamais tout seul (`schedule=None`) : le référentiel Vélib'
change rarement (ouverture/fermeture de station), inutile de le vérifier
chaque nuit. `ingestion.stations_geo` est le plus lent des trois DAGs
(reverse-geocoding via geo.api.gouv.fr, ~6-8 min la première fois) — on
le déclenche à la main depuis l'UI Airflow quand on sait que le
référentiel a changé.
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
