# Image Airflow (orchestration) étendue avec les dépendances de nos
# propres scripts (ingestion météo/calendriers, réentraînement ML), pour
# que les DAGs puissent les lancer directement avec BashOperator sans
# conteneur séparé par tâche (inutile pour 2-3 DAGs planifiés).
FROM apache/airflow:3.4.0-python3.11

# LightGBM charge libgomp (runtime OpenMP) via ctypes au premier import —
# absent de l'image de base (ni pip ni le wheel ne l'embarquent sur Linux).
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
USER airflow

COPY airflow/requirements.txt /tmp/requirements.txt
# Pas de -r ml/requirements.txt ni de --constraint Airflow ici : les deux
# approches testées cassaient soit l'ORM d'Airflow (SQLAlchemy imposé à
# une version trop récente), soit l'installation elle-même (shap exige
# numpy>=2, le fichier de contraintes d'Airflow fige numpy<2 — conflit
# réel, pas contournable par un simple pin). airflow/requirements.txt
# est volontairement minimal (ni SQLAlchemy ni psycopg2-binary, déjà
# fournis par l'image de base + son provider Postgres) ; pip résout donc
# librement ce qui reste, sans toucher aux dépendances internes d'Airflow.
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Code applicatif monté en volume (docker-compose), pas copié ici : un
# changement dans ingestion/ ou ml/ est visible sans rebuild de l'image.
ENV PYTHONPATH=/opt/project
WORKDIR /opt/project
