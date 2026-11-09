# VéloPredict — Contexte du projet (à lire avant toute tâche)

## Le projet
Projet scolaire IPSSI, module Open Data, Sujet 4 (libre), **validé par le professeur**.
VéloPredict prédit la disponibilité des vélos Vélib' (Paris et communes voisines) à 30 et 60 minutes, station par station, à partir de données ouvertes collectées en temps réel.

## Exigences obligatoires du sujet (toutes doivent être couvertes et démontrables)
1. Utiliser de l'Open Data
2. Réaliser une Web App
3. Réaliser une base de données
4. Analyse de données et restitution (data viz : matplotlib et Power BI)
5. Réaliser un modèle de prédiction
6. Utiliser des filtres dans l'application
Bonus valorisé par le prof : une vraie architecture Big Data (Kafka, PySpark, Airflow).

Livrables : présentation orale de 15 à 20 min + dépôt GitHub propre et documenté.

## Sources de données (open data uniquement)
- **Vélib' Métropole, flux GBFS** (temps réel, sans clé). Point d'entrée : `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/gbfs.json`, qui liste les URL de `station_information.json` (nom, coordonnées, capacité) et `station_status.json` (vélos mécaniques et électriques disponibles, bornes libres, `is_renting`, `is_returning`, `last_reported`). Vérifie toujours les URL et les champs réels via `gbfs.json` avant de coder ; ne suppose pas un schéma.
- **Open-Meteo** : `api.open-meteo.com/v1/forecast` (prévisions) et `archive-api.open-meteo.com/v1/archive` (historique). Paris : lat 48.8566, lon 2.3522. Variables : température, précipitations, vent.
- **Jours fériés** : `https://calendrier.api.gouv.fr/jours-feries/metropole.json`
- **Vacances scolaires** : jeu de données « fr-en-calendrier-scolaire » sur data.education.gouv.fr (Paris = zone C).
Ne jamais utiliser de source non ouverte ni scraper un site.

## Architecture cible
```
API Vélib' + Open-Meteo + calendriers
        │ producer Python (toutes les 60 s)
        ▼
  Apache Kafka (topic: velib.station_status)
        │
        ├──► consumer d'archivage ──► TimescaleDB (hypertable des relevés)
        ├──► consumer temps réel  ──► Redis (dernier état de chaque station)
        └──► PySpark Structured Streaming (agrégats par arrondissement, alertes station vide/pleine)
                                  │
                         API FastAPI (REST)
                                  │
                 Web App React + Vite + Leaflet  /  Power BI
Apache Airflow : ingestion météo, calendriers, réentraînement nocturne du modèle
Tout se lance avec docker compose
```

## Stack technique
- Python 3.11+, type hints, `ruff` pour le lint, `pytest` pour les tests
- Kafka : image officielle `apache/kafka` en mode KRaft (sans ZooKeeper)
- TimescaleDB (PostgreSQL) : historique ; Redis : état courant
- FastAPI + SQLAlchemy/psycopg ; validation Pydantic
- ML : pandas, scikit-learn, LightGBM ou XGBoost, SHAP, matplotlib ; modèle sauvegardé avec joblib
- Front : React + Vite + react-leaflet (utiliser des CircleMarker en rendu canvas, il y a environ 1 400 stations)
- Orchestration : Apache Airflow ; streaming : PySpark Structured Streaming

## Structure du dépôt
```
velopredict/
├── CLAUDE.md
├── README.md
├── docker-compose.yml
├── .env.example
├── ingestion/        # producer API → Kafka, chargement météo et calendriers
├── streaming/        # consumers Kafka → TimescaleDB / Redis, job PySpark
├── database/         # schéma SQL, migrations, vues
├── airflow/dags/
├── api/              # FastAPI
├── ml/               # features, entraînement, évaluation, modèle sauvegardé
├── analysis/         # notebooks d'analyse, exports pour Power BI
├── frontend/         # React
├── docs/             # schéma d'architecture, captures, MCD
└── tests/
```

## Règles de travail
- **Travaille phase par phase.** À la fin de chaque phase : résume ce qui a été fait, comment le tester, et attends ma validation avant de passer à la suivante.
- **Priorité absolue : la collecte de données doit tourner en continu le plus tôt possible**, car le modèle dépend de l'historique accumulé. Ne casse jamais la collecte en cours ; signale-moi toute modification qui l'interromprait.
- Pas de secrets dans le code : tout passe par `.env` (fourni sous forme de `.env.example`).
- Code robuste : gestion des erreurs réseau avec retry et backoff, logs clairs, aucune donnée perdue si Kafka ou la base redémarre.
- Chaque composant a un test minimal et une section dans le README (rôle, lancement, vérification).
- Commits petits et explicites, au format Conventional Commits (`feat:`, `fix:`, `docs:`…).
- Préfère une solution simple qui marche à une solution ambitieuse inachevée : d'abord un MVP fonctionnel, ensuite les briques avancées (Spark, Airflow).
- Explique tes choix techniques en une ou deux phrases : nous devrons les justifier à l'oral.

## Règles pour le modèle de prédiction
- Cibles : nombre de vélos disponibles (total, et si possible mécaniques/électriques) à t+30 et t+60 min.
- **Découpage temporel uniquement** (entraînement sur les premiers jours, test sur les derniers), jamais de split aléatoire : sinon fuite de données.
- Toujours comparer à une baseline : « la disponibilité actuelle restera la même » (persistance) et la moyenne historique par station, heure et jour.
- Variables : heure, jour de la semaine, week-end, jour férié, vacances scolaires, météo, disponibilité récente (t, t-15, t-30, t-60), capacité, coordonnées ou arrondissement.
- Métriques : MAE et RMSE par horizon, comparées à la baseline ; graphes matplotlib (réel vs prédit, erreur par heure, importance des variables SHAP) enregistrés dans `ml/reports/`.
