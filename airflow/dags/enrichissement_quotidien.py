"""DAG quotidien : rafraîchit météo et calendriers.

Rôle : garder `weather` (prévisions à jour) et `calendar_days` à jour
pour que les features du modèle (ml/features.py) restent cohérentes.
Les deux scripts sont idempotents (upsert), donc relançables sans risque
même après un échec partiel.

Planifié à 03:00 UTC, avant le réentraînement nocturne (03:30, voir
`reentrainement_modele.py`) : dépendance simple par horaire plutôt qu'un
capteur inter-DAG, suffisant pour deux DAGs qui tournent une fois par
nuit.
"""

from __future__ import annotations

import datetime

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/opt/project"

with DAG(
    dag_id="enrichissement_quotidien",
    description=(
        "Rafraîchit la météo (prévisions + historique) et les calendriers "
        "(jours fériés, vacances scolaires)"
    ),
    schedule="0 3 * * *",
    start_date=datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC),
    catchup=False,
    max_active_runs=1,
    tags=["velopredict", "enrichissement"],
) as dag:
    rafraichir_meteo = BashOperator(
        task_id="rafraichir_meteo",
        bash_command=f"cd {PROJECT_DIR} && python -m ingestion.weather",
    )

    rafraichir_calendriers = BashOperator(
        task_id="rafraichir_calendriers",
        bash_command=f"cd {PROJECT_DIR} && python -m ingestion.calendar_days",
    )

    # Indépendants l'un de l'autre (tables différentes) : en parallèle.
    [rafraichir_meteo, rafraichir_calendriers]
