"""DAG nocturne : réentraîne le modèle de prédiction sur l'historique
accumulé depuis la dernière fois (`ml/retrain.py`, voir aussi
`ml/reports/RESULTATS.md`).

Planifié à 03:30 UTC, après `enrichissement_quotidien` (03:00), pour que
les features météo utilisées par le modèle soient à jour avant
l'entraînement.

`ml/retrain.py` écrit les nouveaux `.joblib` dans `ml/models/` (volume
partagé avec le conteneur `api`, monté en lecture seule côté API) : un
redémarrage de l'API suffit pour servir le modèle réentraîné, pas besoin
de rebuild. Pas automatisé ici volontairement — un changement de modèle
reste une décision qu'on valide avant de la pousser en service.
"""

from __future__ import annotations

import datetime

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/opt/project"

with DAG(
    dag_id="reentrainement_modele",
    description="Réentraîne le modèle LightGBM sur tout l'historique disponible",
    schedule="30 3 * * *",
    start_date=datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC),
    catchup=False,
    max_active_runs=1,
    tags=["velopredict", "ml"],
) as dag:
    reentrainer = BashOperator(
        task_id="reentrainer_modele",
        bash_command=f"cd {PROJECT_DIR} && python -m ml.retrain",
    )
