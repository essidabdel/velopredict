# Image Airflow (orchestration) étendue avec les dépendances du seul DAG
# du projet (ingestion.weather, ingestion.calendar_days, ingestion.stations
# — enrichissement_quotidien), pour qu'il puisse les lancer directement
# avec BashOperator sans conteneur séparé par tâche.
FROM apache/airflow:3.4.0-python3.11

COPY airflow/requirements.txt /tmp/requirements.txt
# Pas de -r ingestion/requirements.txt (copie complète) : volontairement
# sans SQLAlchemy ni psycopg2-binary, déjà fournis par l'image de base +
# son provider Postgres — les réinstaller casse l'ORM interne d'Airflow
# (confirmé : une version différente force une recréation incompatible
# des modèles SQLAlchemy d'Airflow au démarrage).
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Code applicatif monté en volume (docker-compose), pas copié ici : un
# changement dans ingestion/ est visible sans rebuild de l'image.
ENV PYTHONPATH=/opt/project
WORKDIR /opt/project
