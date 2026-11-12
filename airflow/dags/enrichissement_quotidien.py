"""DAG quotidien : rafraîchit météo, calendriers et le référentiel stations.

Rôle : garder `weather` (prévisions à jour), `calendar_days` et `stations`
à jour pour que les features du modèle (ml/features.py) restent
cohérentes, et qu'une nouvelle station Vélib' apparaisse sur la carte dès
le lendemain de son ouverture plutôt que de rester invisible en attendant
un déclenchement manuel. Les trois scripts sont idempotents (upsert),
donc relançables sans risque même après un échec partiel.

`ingestion.stations` seulement ici, pas `ingestion.stations_geo` (le
géocodage commune/arrondissement, ~6-8 min) : trop lent pour un DAG
quotidien alors que la position change rarement une fois la station
créée. Le géocodage complet reste dans `maj_referentiel_stations.py`
(déclenchement manuel) — une nouvelle station apparaît donc sur la carte
sans commune/arrondissement tant que ce second DAG n'a pas tourné.

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
        "Rafraîchit la météo (prévisions + historique), les calendriers "
        "(jours fériés, vacances scolaires) et le référentiel stations"
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

    rafraichir_stations = BashOperator(
        task_id="rafraichir_stations",
        bash_command=f"cd {PROJECT_DIR} && python -m ingestion.stations",
    )

    # Indépendants les uns des autres (tables différentes) : en parallèle.
    [rafraichir_meteo, rafraichir_calendriers, rafraichir_stations]
