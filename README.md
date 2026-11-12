# VéloPredict

Prédiction de la disponibilité des vélos **Vélib'** (Paris et communes
voisines) à **30 et 60 minutes**, station par station, à partir de données
open data collectées en temps réel.

Projet réalisé dans le cadre du module **Open Data** (IPSSI) — Sujet 4
(libre).

## Sommaire

- [Objectif](#objectif)
- [Architecture](#architecture)
- [Stack technique](#stack-technique)
- [Sources de données](#sources-de-données-open-data)
- [Structure du dépôt](#structure-du-dépôt)
- [Prérequis](#prérequis)
- [Lancement](#lancement)
- [Composants](#composants)
- [Analyses (Phase 4)](#analyses-phase-4)
- [Connecter Power BI](#connecter-power-bi)
- [Outils d'inspection (démo / présentation)](#outils-dinspection-démo--présentation)
- [Airflow — orchestration (bonus Phase 7)](#airflow--orchestration-bonus-phase-7)
- [Vérifier que tout fonctionne](#vérifier-que-tout-fonctionne)
- [Captures d'écran](#captures-décran)
- [État d'avancement](#état-davancement)

## Objectif

Le projet couvre les exigences du sujet :

1. Utilisation d'Open Data (Vélib' GBFS, Open-Meteo, calendriers officiels)
2. Web App de visualisation et de prédiction
3. Base de données (historique des relevés)
4. Analyse de données et restitution (matplotlib, Power BI)
5. Modèle de prédiction (disponibilité à t+30 / t+60 min)
6. Filtres dans l'application (station, zone, horizon de prédiction...)

En bonus, une architecture Big Data est mise en place : **Kafka**,
**PySpark Structured Streaming** et **Apache Airflow**.

## Architecture

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
```

Tout le stack se lance avec `docker compose`.

## Stack technique

| Domaine        | Outils |
|-----------------|--------|
| Langage          | Python 3.11+ (type hints), `ruff` (lint), `pytest` (tests) |
| Streaming        | Apache Kafka (image `apache/kafka`, mode KRaft, sans ZooKeeper) |
| Bases de données | TimescaleDB (historique), Redis (état courant) |
| API              | FastAPI, SQLAlchemy / psycopg, Pydantic |
| Machine Learning | pandas, scikit-learn, LightGBM / XGBoost, SHAP, matplotlib, joblib |
| Frontend         | React, Vite, react-leaflet (CircleMarker en rendu canvas) |
| Orchestration    | Apache Airflow |
| Traitement       | PySpark Structured Streaming |

## Sources de données (open data)

- **Vélib' Métropole — GBFS** (temps réel, sans clé) : point d'entrée
  [`gbfs.json`](https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/gbfs.json),
  qui référence `station_information.json` (nom, coordonnées, capacité) et
  `station_status.json` (vélos mécaniques / électriques disponibles, bornes
  libres, `is_renting`, `is_returning`, `last_reported`).
- **Open-Meteo** : prévisions (`api.open-meteo.com/v1/forecast`) et
  historique (`archive-api.open-meteo.com/v1/archive`) pour Paris
  (lat 48.8566, lon 2.3522).
- **Jours fériés** : `calendrier.api.gouv.fr/jours-feries/metropole.json`.
- **Vacances scolaires** : jeu de données « fr-en-calendrier-scolaire »
  (data.education.gouv.fr, zone C pour Paris).
- **Géocodage commune/arrondissement** : `geo.api.gouv.fr/communes`
  (reverse-geocoding officiel par coordonnées).

Aucune source non ouverte, aucun scraping.

### Attribution — historique backfillé

Le flux GBFS officiel Vélib' est un instantané temps réel : il n'expose
aucun historique. Pour disposer de plusieurs semaines de données réelles
dès le lancement du projet (plutôt que d'attendre que notre propre
collecte s'accumule), `station_status` est complétée par l'archive
communautaire **[tibzsecondaire/velib-data](https://github.com/tibzsecondaire/velib-data)**,
qui republie en continu les mêmes données officielles GBFS Vélib'
Métropole, sous licence **[Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/)**
— la même licence que le jeu de données officiel publié par la Ville de
Paris sur data.gouv.fr. Les lignes importées sont marquées
`source = 'backfill_github'` dans `station_status` (vs `'live'` pour notre
propre collecte), et leur fiabilité par jour est documentée dans
`backfill_day_quality` (voir `ingestion/backfill.py`).

## Structure du dépôt

```
velopredict/
├── CLAUDE.md         # contexte et règles du projet
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
├── frontend/         # React + Vite + react-leaflet
├── docs/             # schéma d'architecture, captures, MCD
└── tests/
```

## Prérequis

- [Docker](https://www.docker.com/) + Docker Compose v2
- Python 3.11+
- Node.js 20+ (pour développer le frontend hors Docker ; le build en
  conteneur n'en a pas besoin sur la machine hôte)

> Si un PostgreSQL local tourne déjà sur la machine (service Windows,
> install native...), il occupe souvent le port 5432 : TimescaleDB est donc
> exposé sur le port hôte **5433** par défaut (`POSTGRES_PORT` dans `.env`)
> pour éviter tout conflit. Le port interne au réseau Docker reste 5432.

## Lancement

```bash
# 1. Copier la configuration d'exemple
cp .env.example .env

# 2. Démarrer toute la stack (Kafka, TimescaleDB, Redis, producer,
#    archiver, live, api, frontend)
docker compose up -d --build

# 3. Suivre les logs si besoin
docker compose logs -f producer archiver live api
```

Le schéma SQL (`database/migrations/`) est appliqué automatiquement au
premier démarrage de TimescaleDB (volume vide). L'API est accessible sur
`http://localhost:8000` (`/docs` pour Swagger) et la Web App sur
`http://localhost:3000`.

Pour charger/rafraîchir le référentiel des stations et les données
d'enrichissement (changent rarement ou périodiquement — pas besoin de les
faire tourner en continu ; seront orchestrés par Airflow en Phase 7) :

```bash
# Depuis un venv Python 3.11+ avec ingestion/requirements.txt installé
python -m ingestion.stations        # référentiel stations (nom, capacité, coordonnées)
python -m ingestion.weather         # historique + prévisions météo (Paris)
python -m ingestion.calendar_days   # jours fériés + vacances scolaires zone C
python -m ingestion.stations_geo    # commune/arrondissement par station (~6-8 min la 1ère fois)
pip install -r ingestion/requirements-backfill.txt && python -m ingestion.backfill  # historique (35 jours, voir Attribution)
pip install -r ml/requirements.txt && python -m ml.retrain  # entraîne le modèle (requis pour /prediction)
```

## Composants

### `ingestion/producer` — producer Kafka

- **Rôle** : interroge `station_status.json` (résolu dynamiquement via
  `gbfs.json`) toutes les `INGESTION_POLL_INTERVAL_SECONDS` (60s par
  défaut) et publie chaque station comme un message JSON dans le topic
  Kafka `velib.station_status` (clé = `station_id`). Retry + backoff
  exponentiel sur les erreurs réseau ; ne s'arrête jamais sur une erreur
  ponctuelle (le cycle en échec est simplement journalisé et retenté au
  cycle suivant).
- **Lancement** : `docker compose up -d producer` (fait partie de la stack
  par défaut), ou en local : `python -m ingestion.producer`.
- **Vérification** : `docker compose logs -f producer` doit afficher un
  "Cycle terminé : 1522 stations publiées" toutes les ~60s.

### `ingestion/stations` — chargement du référentiel

- **Rôle** : charge `station_information.json` (nom, coordonnées,
  capacité) dans la table `stations` via un upsert. Script ponctuel, pas
  un service continu.
- **Lancement** : `python -m ingestion.stations` (nécessite `DATABASE_URL`
  pointant vers TimescaleDB, ex. `postgresql://velopredict:change-me@localhost:5433/velopredict`).
- **Vérification** : `SELECT count(*) FROM stations;` doit renvoyer 1522.

### `database/` — schéma TimescaleDB

- **Rôle** : `database/migrations/001_init_schema.sql` crée l'extension
  `timescaledb`, la table `stations` (référentiel) et l'hypertable
  `station_status` (historique des relevés). Pas de clé étrangère entre
  les deux : l'archivage de l'historique ne doit jamais être bloqué par un
  référentiel pas encore chargé.
- **Lancement** : appliqué automatiquement par TimescaleDB au premier
  démarrage (monté sur `/docker-entrypoint-initdb.d`).
- **Vérification** : voir la section [Vérifier que les données arrivent](#vérifier-que-les-données-arrivent).

### `ingestion/weather` — météo (Open-Meteo)

- **Rôle** : charge l'historique horaire (`archive-api.open-meteo.com`,
  depuis la date du premier relevé dans `station_status` jusqu'à hier)
  puis les prévisions horaires à 7 jours (`api.open-meteo.com`) pour le
  point fixe Paris, dans la table `weather`. Idempotent : upsert sur `ts`
  où une prévision ne peut jamais écraser un relevé archive déjà confirmé
  pour la même heure (voir `WHERE` de `UPSERT_SQL`), mais l'archive peut
  toujours remplacer une prévision une fois l'historique disponible.
- **Lancement** : `python -m ingestion.weather`. À relancer périodiquement
  (ex. quotidien via Airflow) pour rafraîchir les prévisions et compléter
  l'historique.
- **Vérification** : `SELECT source, count(*) FROM weather GROUP BY source;`

### `ingestion/calendar_days` — jours fériés + vacances scolaires

- **Rôle** : charge les jours fériés (`calendrier.api.gouv.fr`, toutes
  années) et les vacances scolaires zone C de Paris
  (`data.education.gouv.fr`, dataset `fr-en-calendrier-scolaire`, filtré
  sur `zones="Zone C" and location="Paris"`) dans `calendar_days`. Les
  entrées réservées aux seuls enseignants (pré-rentrée d'été) sont
  exclues. Table volontairement **sparse** : un jour absent de la table
  est un jour ordinaire (ni férié, ni vacances) — les requêtes doivent
  faire un `LEFT JOIN` + `COALESCE(..., false)`.
- **Lancement** : `python -m ingestion.calendar_days`. Idempotent (upsert
  sur `day`, les deux sources n'écrivant jamais sur les mêmes colonnes).
- **Vérification** : `SELECT * FROM calendar_days WHERE day = '2026-11-01';`
  doit montrer `is_public_holiday = true` **et** `is_school_holiday = true`
  (Toussaint).

### `ingestion/stations_geo` — commune / arrondissement des stations

- **Rôle** : déduit la commune (ou l'arrondissement pour Paris/Lyon/
  Marseille) de chaque station à partir de ses coordonnées, via
  `geo.api.gouv.fr` (reverse-geocoding officiel, pas de fichier de
  contours à gérer). Essaie d'abord `type=arrondissement-municipal`, puis
  retombe sur la commune standard si vide.
- **Lancement** : `python -m ingestion.stations_geo` (≈6-8 min pour 1522
  stations la première fois). La recherche "commune standard" de cette API
  est lente côté serveur (1 à 8s/appel, mesuré empiriquement) ; les
  requêtes sont donc parallélisées (10 threads par défaut, `--workers` pour
  ajuster) plutôt que ralenties par une pause séquentielle. Par défaut,
  seules les stations sans `commune_code` sont interrogées — relance
  rapide et sans risque de doublon (`UPDATE` sur `station_id`, jamais
  d'`INSERT`). `--refresh` force une ré-interrogation complète.
- **Vérification** : `SELECT commune_nom, count(*) FROM stations GROUP BY commune_nom ORDER BY 2 DESC LIMIT 5;`

### `ingestion/backfill` — historique depuis l'archive communautaire ODbL

- **Rôle** : importe `daily/*.parquet` + `daily/index.csv` de
  [tibzsecondaire/velib-data](https://github.com/tibzsecondaire/velib-data)
  dans `station_status` (colonne `source = 'backfill_github'`, vs `'live'`
  pour notre collecte — voir [Attribution](#attribution--historique-backfillé)).
  Peuple aussi `backfill_day_quality` (un jour UTC = une ligne, `reliable`
  = `max_gap_minutes <= 60`) à partir de `daily/index.csv`, pour que
  `v_training_eligible_status` (migration 004) puisse exclure du jeu
  d'entraînement les jours trop troués — en pratique le 2026-10-26 et le
  2026-11-02 au 2026-11-08 au moment de l'import. La donnée brute de ces
  jours reste dans `station_status` (pas perdue, juste exclue de cette vue).
- **Lancement** : nécessite des dépendances non installées dans l'image
  Docker du producer (`pip install -r ingestion/requirements-backfill.txt`),
  puis `python -m ingestion.backfill`. Prend quelques minutes (téléchargement
  + insertion de plusieurs millions de lignes).
- **Vérification** : `SELECT source, count(*) FROM station_status GROUP BY source;`
  et `SELECT day, max_gap_minutes, reliable FROM backfill_day_quality WHERE NOT reliable ORDER BY day;`

### `streaming/archiver` — consumer Kafka → TimescaleDB

- **Rôle** : consomme `velib.station_status`, accumule les messages par
  lots (500 lignes ou 5 secondes, selon ce qui arrive en premier) et les
  insère dans `station_status` via `execute_values` avec
  `ON CONFLICT (station_id, ts) DO NOTHING`. Les offsets Kafka ne sont
  commités qu'après succès de l'insertion du lot : en cas de coupure de
  TimescaleDB, le lot est retenté indéfiniment plutôt qu'abandonné, et en
  cas de redémarrage de l'archiver avant le commit, les messages
  retraités sont simplement ignorés par la contrainte d'unicité.
- **Lancement** : `docker compose up -d archiver` (fait partie de la stack
  par défaut), ou en local : `python -m streaming.archiver`.
- **Vérification** : `docker compose logs -f archiver` doit afficher des
  "Batch archivé : N lignes" réguliers.

### `streaming/live` — consumer Kafka → Redis

- **Rôle** : consomme `velib.station_status` (groupe de consumers séparé
  de l'archiver — les deux lisent indépendamment tous les messages) et
  maintient dans Redis le dernier état connu de chaque station
  (`station:{id}` en JSON + un index `stations:index`), pour une lecture
  instantanée par l'API. Même robustesse que l'archiver (batch + retry
  indéfini + commit des offsets après écriture réussie), mais sans besoin
  de déduplication : écraser deux fois la même valeur dans Redis est
  inoffensif.
- **Lancement** : `docker compose up -d live`, ou en local :
  `python -m streaming.live`.
- **Vérification** : `docker compose logs -f live` doit afficher des
  "Batch écrit dans Redis : N stations" réguliers.

### `api/` — FastAPI

- **Rôle** : expose la disponibilité des stations en combinant le
  référentiel Postgres (nom, capacité, commune) et l'état temps réel Redis.
  - `GET /stations` — liste filtrable par `arrondissement` (recherche
    partielle sur la commune/l'arrondissement), `velo`
    (`mecanique`/`electrique`), `etat` (`vide`/`pleine`/`disponible`) et
    `recherche` (nom de station).
  - `GET /stations/{id}` — détail d'une station (état actuel + capacité),
    404 si inconnue.
  - `GET /stations/{id}/history?hours=24` — historique TimescaleDB de la
    station (1 à 168h), 404 si la station n'existe pas.
  - `GET /stations/{id}/prediction` — vélos disponibles prédits à t+30 et
    t+60min (modèle LightGBM, voir `ml/`) ; 404 si la station est inconnue
    ou si l'historique récent est insuffisant, 503 si aucun modèle n'a
    encore été entraîné.
  - `GET /stats/overview` — vélos disponibles au total, stations
    vides/pleines, sur l'ensemble du réseau.
  - `GET /health` — vérification de vie.
- **Lancement** : `docker compose up -d api`, ou en local :
  `uvicorn api.main:app --reload`. Documentation interactive Swagger sur
  `http://localhost:8000/docs` (et ReDoc sur `/redoc`).
- **Tests** : `pytest tests/api` — les endpoints sont testés avec
  `TestClient` et des doubles de DB/Redis (`app.dependency_overrides`), pas
  besoin d'infra réelle pour les lancer.
- **Vérification manuelle** :
  ```bash
  curl http://localhost:8000/stats/overview
  curl "http://localhost:8000/stations?arrondissement=16e&etat=disponible"
  ```

### `ml/` — modèle de prédiction

- **Rôle** : prédit le nombre total de vélos disponibles par station à
  t+30 et t+60 minutes. Pipeline complet : `ml/features.py` (construction
  des features, grille 15 min + tolérance 30 min, variables listées dans
  CLAUDE.md), `ml/baselines.py` (persistance + moyenne historique),
  `ml/train.py` (découpage temporel strict, régression linéaire +
  LightGBM), `ml/classify.py` (classifieur "station vide" avec seuil
  réglé sur validation), `ml/evaluate.py` (MAE/RMSE, graphiques),
  `ml/evaluate_live.py` (ré-évaluation sur la collecte live, test
  indépendant), `ml/predict.py` (inférence en direct, utilisé par l'API).
- **Lancement / ré-entraînement** :
  ```bash
  pip install -r ml/requirements.txt
  python -m ml.retrain
  ```
  Réutilise toute la fenêtre disponible dans `v_training_eligible_status`
  par défaut (`--start`/`--end` pour figer une fenêtre). Sauvegarde les
  modèles dans `ml/models/` (gitignoré — l'API les lit via un volume monté,
  voir `docker-compose.yml`) et les graphiques/métriques dans
  `ml/reports/`.
- **Résultats** : voir **[`ml/reports/RESULTATS.md`](ml/reports/RESULTATS.md)**
  — MAE/RMSE par horizon vs 4 autres modèles/baselines, importance SHAP,
  dates précises du train/test, MAE sur les stations qui changent
  vraiment, classifieur "station vide" dédié avec seuil réglé sur
  validation (précision/rappel/F1, + l'événement "devient vide"), un
  second jeu de test (2-3 novembre) et un test sur données live, limites.
  LightGBM bat la persistance sur les deux horizons (jusqu'à -13% de MAE
  sur les lignes où la disponibilité change réellement, et +6% de F1 sur
  la classification "vide dans 30min" une fois le seuil correctement
  réglé — un seuil naïf à 0.5 inversait ce résultat, voir le rapport §9).
- **Tests** : `pytest tests/ml` — logique pure (découpage temporel,
  baselines, gestion du changement d'heure, jointure par horodatage réel,
  filtrage des stations inactives, réglage de seuil) testée sans DB ni
  modèle réel.
- **Note technique** : sur cette machine Windows, entraîner LightGBM et
  scikit-learn dans le même process (ou importer `matplotlib`/`shap`
  avant LightGBM) provoque un crash natif reproductible — contourné
  (LightGBM mono-thread, régression linéaire isolée en sous-process,
  imports différés). Détails dans `ml/reports/RESULTATS.md` §6 et les
  commentaires du code ; sans impact sur la qualité des modèles.

### `frontend/` — Web App (React + Vite + react-leaflet)

- **Rôle** : consulte l'API FastAPI depuis le navigateur, sans aucun appel
  serveur intermédiaire (le build nginx sert uniquement des fichiers
  statiques). 5 pages :
  - **Carte** (`/`) — les ~1522 stations en `CircleMarker` (rendu canvas,
    `preferCanvas`), couleur **et** libellé par état (vide, disponibilité
    faible ≤20% de la capacité, disponible, pleine, inconnue), légende
    visible, actualisation automatique toutes les 60s.
  - **Recherche + filtres** — recherche par nom de station, et filtres
    commune/arrondissement, type de vélo, état, combinables entre eux et
    reflétés dans l'URL (`?arrondissement=16e&velo=mecanique&etat=disponible`)
    via `useSearchParams` — un lien copié/partagé reproduit exactement la
    même vue.
  - **Fiche station** (`/stations/:id`) — état actuel, courbe des 24
    dernières heures (recharts), prédictions à t+30/t+60min (nombre de
    vélos) et le risque de pénurie à 30min affiché **uniquement** comme un
    niveau discret (faible/moyen/élevé), jamais une probabilité brute (voir
    `ml/predict.py::classify_risk_level`).
  - **Tableau de bord** (`/dashboard`) — indicateurs globaux (vélos
    disponibles, stations vides/pleines) + 3 graphiques (répartition par
    état, mécanique vs électrique, communes avec le plus de stations
    vides).
  - **À propos** (`/about`) — sources open data, attribution ODbL, méthode
    et limites du modèle.
  - États de chargement (squelettes à la forme du contenu final, pas un
    simple spinner générique) et d'erreur gérés sur chaque page (message
    clair + bouton « Réessayer » si l'API est injoignable, voir
    [captures d'écran](#captures-décran)) ; état vide dédié quand des
    filtres ne renvoient aucune station.
  - Design responsive avec nav mobile dédiée (menu plein écran sous
    760px, pas un simple retour à la ligne) ; mode sombre (suit la
    préférence système, bascule mémorisée en `localStorage`) ;
    accessibilité clavier (lien d'évitement, focus visible partout,
    animations réduites si `prefers-reduced-motion`).
- **Lancement** :
  ```bash
  docker compose up -d --build frontend   # http://localhost:3000 (nginx)

  # ou en dev, avec rechargement à chaud :
  cd frontend && npm install && npm run dev   # http://localhost:5173
  ```
  `VITE_API_BASE_URL` (défaut `http://localhost:8000`) est inliné **au
  build** par Vite (variable d'environnement classique inutile au
  runtime) — voir `frontend/Dockerfile` et `FRONTEND_PORT`/
  `VITE_API_BASE_URL` dans `.env.example`.
- **Vérification** :
  ```bash
  curl -s -o /dev/null -w "%{http_code}
" http://localhost:3000/            # 200
  curl -s -o /dev/null -w "%{http_code}
" http://localhost:3000/dashboard   # 200 (fallback SPA nginx)
  cd frontend && npm run lint && npx tsc -b   # oxlint + vérification des types
  ```
- **Versioning du modèle** : le modèle servi par l'API est figé au tag git
  `model-v1` depuis le début de cette phase — voir la note en tête de
  [`ml/reports/RESULTATS.md`](ml/reports/RESULTATS.md).

### `analysis/` — notebooks et exports Power BI

- **Rôle** : 5 notebooks Jupyter (commentés en français, une conclusion par
  graphique) couvrant les analyses demandées — voir
  [Analyses](#analyses-phase-4) ci-dessous. S'appuient sur 5 vues SQL
  (`database/migrations/003_analysis_views.sql`) également exportées en
  CSV pour Power BI par `analysis/export_powerbi.py`.
- **Lancement** :
  ```bash
  pip install -r analysis/requirements.txt
  cd analysis
  jupyter lab                        # ouvrir/relancer les notebooks à la main
  python export_powerbi.py           # régénérer les CSV dans analysis/exports/
  ```
- **Note technique (spécifique à cette machine Windows)** : le lancement
  d'un noyau Jupyter dans un sous-processus séparé est bloqué par une
  stratégie de contrôle d'application Windows (Smart App Control/WDAC),
  avec l'erreur `WinError 4551`. Si `jupyter lab` butte dessus en essayant
  d'exécuter une cellule, utilise `analysis/_execute_inplace.py` : il
  exécute le notebook dans le même process Python (sans sous-processus
  noyau) et réinjecte proprement les sorties (texte + figures) dans le
  fichier `.ipynb` :
  ```bash
  python analysis/_execute_inplace.py analysis/01_disponibilite_quotidienne.ipynb
  ```
  Par ailleurs, `pandas==3.1.1` (trop récent, pas encore "de confiance"
  pour cette même stratégie) déclenchait un blocage au chargement d'une de
  ses DLL internes : `analysis/requirements.txt` épingle `pandas==2.2.3`,
  qui fonctionne sans problème.
- **Vérification** : rouvrir un notebook exécuté — chaque graphique doit
  avoir une sortie (tableau ou image) et une cellule de conclusion juste
  en dessous.

## Analyses (Phase 4)

| Notebook | Analyse |
|---|---|
| `01_disponibilite_quotidienne.ipynb` | Disponibilité moyenne par heure, semaine vs week-end |
| `02_flux_domicile_travail.ipynb` | Stations qui se vident le matin / se remplissent le soir + carte |
| `03_meteo_usage.ipynb` | Effet pluie/température sur l'usage (proxy : mouvement horaire de stock) |
| `04_mecanique_vs_electrique.ipynb` | Comparaison vélos mécaniques vs électriques |
| `05_penurie_arrondissements.ipynb` | Classement des communes/arrondissements les plus souvent en pénurie |

**Couverture des données** : au-delà de notre propre collecte en direct,
`station_status` inclut un **historique réel de 35 jours** (2026-10-05 à
2026-11-08) importé depuis l'archive communautaire ODbL
`tibzsecondaire/velib-data` (voir
[Attribution](#attribution--historique-backfillé) et
`ingestion/backfill.py`) — le flux GBFS officiel Vélib' n'exposant aucun
historique propre. Chaque notebook commence quand même par vérifier la
couverture réelle des données (bonne pratique à conserver), et les
conclusions restent honnêtes sur les limites qui demeurent (notamment la
confusion possible entre effet météo et cycle jour/nuit dans le notebook
météo). Relance les notebooks (ou `_execute_inplace.py`) périodiquement
pour les rafraîchir à mesure que `producer`/`archiver` collectent plus de
données en direct.

## Connecter Power BI

Deux façons de récupérer les données, à choisir selon le contexte :

### Option A — connexion directe à TimescaleDB (recommandée)

Power BI Desktop lit TimescaleDB comme un PostgreSQL standard (les vues
`v_*` apparaissent comme des tables normales) :

1. Installer le driver **Npgsql** pour Power BI (le connecteur PostgreSQL
   de Power BI en a besoin) : <https://github.com/npgsql/npgsql/releases>
   → télécharger le dernier `.msi` et l'installer (fermer Power BI avant).
2. Dans Power BI Desktop : **Obtenir les données** → **Base de données
   PostgreSQL**.
3. Serveur : `localhost:5433` (le port hôte exposé par `docker-compose.yml`
   — adapter si `POSTGRES_PORT` a été changé dans `.env`).
   Base de données : `velopredict`.
4. Mode de données : **Import** (simple pour un projet de cette taille) ou
   **DirectQuery** (toujours à jour, mais revalide chaque visuel à chaque
   interaction — Import est recommandé pour la présentation orale).
5. Identifiants : `velopredict` / la valeur de `POSTGRES_PASSWORD` (dans
   `.env`), authentification "Base de données".
6. Dans le navigateur, sélectionner les vues (`v_hourly_availability`,
   `v_station_flux_domicile_travail`, `v_hourly_movement_weather`,
   `v_bike_type_share`, `v_penurie_par_commune`) plutôt que les tables
   brutes — elles sont déjà agrégées et prêtes à l'emploi.

### Option B — import des CSV exportés

Si la machine qui fait tourner Power BI n'a pas accès au réseau Docker
(ou pour partager les données sans donner les identifiants de la base) :

1. `python analysis/export_powerbi.py` (régénère les CSV dans
   `analysis/exports/`).
2. Dans Power BI Desktop : **Obtenir les données** → **Texte/CSV**, puis
   sélectionner chaque fichier dans `analysis/exports/`.
3. Pour rafraîchir après une nouvelle collecte : relancer le script export
   puis **Actualiser** dans Power BI (si les CSV sont au même chemin, le
   rafraîchissement reprend les mêmes requêtes automatiquement).

## Outils d'inspection (démo / présentation)

Trois interfaces web en lecture, utiles pour montrer concrètement le
pipeline Kafka → TimescaleDB/Redis à l'oral — **pas démarrées** par
`docker compose up -d` (profil Docker séparé, pour ne pas alourdir le
lancement normal) :

```bash
docker compose --profile tools up -d   # démarre les 3 interfaces
docker compose --profile tools down    # les arrête (le reste continue de tourner)
```

| Interface | URL | Ce que ça montre |
|---|---|---|
| **Kafka UI** | http://localhost:8081 | Le topic `velib.station_status`, son nombre de messages/sa taille, et le contenu JSON brut de chaque message (onglet *Messages*) |
| **Adminer** | http://localhost:8082 | Les tables/vues PostgreSQL/TimescaleDB — se connecter avec Système **PostgreSQL**, Serveur `timescaledb`, Utilisateur/Base `velopredict`, mot de passe = `POSTGRES_PASSWORD` du `.env` |
| **Redis Commander** | http://localhost:8083 | Les clés `station:<id>` (dernier état connu) — console `redis>` en bas de page pour taper `get station:6245` par exemple |

> ⚠️ Démarrer ce profil recrée `producer`/`archiver`/`live`/`api` si le
> fichier `.env` vient de changer (Docker Compose invalide leur config
> dès que `.env` change, même si les variables qu'ils utilisent sont
> identiques) : coupure de quelques secondes, aucune perte de données
> (Kafka conserve les messages, les inserts sont idempotents). Les
> conteneurs `kafka`/`timescaledb`/`redis` eux-mêmes ne redémarrent pas.

## Airflow — orchestration (bonus Phase 7)

Orchestre deux tâches récurrentes (enrichissement, réentraînement) plus
une tâche manuelle (référentiel stations), comme prévu dans
l'architecture cible du `CLAUDE.md`. **Pas démarré** par
`docker compose up -d` (profil Docker séparé — Airflow + son metastore
PostgreSQL dédié sont lourds pour un bonus optionnel) :

```bash
docker compose --profile airflow up -d     # démarre Airflow (~1-2 min au premier lancement)
docker compose --profile airflow down      # l'arrête (le reste continue de tourner)
```

Interface : **http://localhost:8080**. Identifiant `admin`, mot de passe
généré au premier démarrage et affiché une seule fois dans les logs :

```bash
docker compose logs airflow-apiserver | grep "Password for user"
```

(Si tu as perdu ce mot de passe après un `docker compose --profile airflow down -v` qui supprime le volume `airflow_db_data`, un nouveau sera régénéré et réaffiché au prochain démarrage.)

| DAG | Planning | Rôle |
|---|---|---|
| `enrichissement_quotidien` | tous les jours à 03:00 UTC | Rafraîchit météo (prévisions + historique) et calendriers |
| `reentrainement_modele` | tous les jours à 03:30 UTC | Relance `ml.retrain` sur tout l'historique disponible — écrit les nouveaux `.joblib` dans `ml/models/`, lus directement par l'API (redémarrer `api` pour les servir) |
| `maj_referentiel_stations` | déclenchement manuel uniquement | Référentiel des stations + géocodage commune/arrondissement (rarement nécessaire, ~6-8 min) |

Un DAG nouvellement créé est **en pause par défaut** (comportement
standard Airflow, pas un bug) : bascule l'interrupteur dans l'interface,
ou en CLI :

```bash
docker compose exec airflow-scheduler airflow dags unpause reentrainement_modele
docker compose exec airflow-scheduler airflow dags trigger reentrainement_modele   # test immédiat
docker compose exec airflow-scheduler airflow dags list-runs -d reentrainement_modele
```

### Choix techniques et pièges résolus

- **Airflow 3.4 plutôt que 2.x** : Airflow 2.x (même 2.11.2, la dernière
  version 2.x) impose SQLAlchemy 1.4, incompatible avec le
  `pd.read_sql` de pandas 2.2+ (`AttributeError: 'Engine' object has no
  attribute 'cursor'`). Airflow 3 utilise SQLAlchemy 2.0, qui résout le
  problème — mais change l'architecture : webserver → `api-server`,
  scheduler qui ne parse plus les DAGs seul → `dag-processor` séparé
  (les deux sont déployés ici), et un nouveau système de jetons JWT entre
  les tâches et l'API (`AIRFLOW__API_AUTH__JWT_SECRET` doit être
  identique sur tous les conteneurs Airflow, sinon `Invalid auth token`).
- **Image Airflow étendue (`airflow/Dockerfile`)**, pas un conteneur par
  script : `ingestion.weather`, `ingestion.calendar_days` et `ml.retrain`
  tournent directement dans l'image Airflow via `BashOperator`.
  `airflow/requirements.txt` est volontairement **différent** de
  `ingestion/requirements.txt`/`ml/requirements.txt` : sans SQLAlchemy ni
  psycopg2-binary (fournis par Airflow + son provider Postgres — les
  réinstaller casse l'ORM interne d'Airflow), mais avec les **mêmes**
  versions de numpy/pandas/scikit-learn/joblib/lightgbm que
  `ml/requirements.txt` = `api/requirements.txt` : ce sont elles qui
  (dé)sérialisent les `.joblib`, un écart entre l'environnement qui
  entraîne et celui qui sert le modèle est le genre de bug qui ne se voit
  qu'au chargement.
- **`libgomp1`** (runtime OpenMP) ajouté via `apt-get` : LightGBM le
  charge au premier import, absent de l'image Airflow de base.
- Testé de bout en bout : les deux DAGs planifiés ont réellement tourné
  avec succès (requêtes Open-Meteo/calendrier.api.gouv.fr en direct pour
  le premier ; features sur ~9,4M lignes + entraînement + graphiques SHAP
  pour le second, ~5min30).

## Vérifier que tout fonctionne

```bash
# État et santé des services
docker compose ps

# Kafka : lister les topics (doit afficher velib.station_status)
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

# TimescaleDB : se connecter et vérifier l'extension
docker compose exec timescaledb psql -U velopredict -d velopredict -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';"

# Redis : ping (demande le mot de passe défini dans .env)
docker compose exec redis redis-cli -a change-me ping

# Producer + archiver : logs
docker compose logs -f producer archiver
```

### Vérifier que les données arrivent

```sql
-- Une "vague" d'environ 1522 lignes doit apparaître toutes les ~60s
SELECT ts, count(*) AS nb_stations
FROM station_status
WHERE ts > now() - INTERVAL '10 minutes'
GROUP BY ts
ORDER BY ts DESC;

-- Le retard depuis le dernier relevé doit rester sous 2 minutes
-- si producer + archiver tournent normalement
SELECT now() - max(ts) AS retard FROM station_status;
```

### Jointure enrichie (aperçu des features ML futures)

```sql
SELECT
    ss.station_id, s.name, s.commune_nom,
    ss.ts, ss.num_mechanical, ss.num_ebike, ss.num_docks_available,
    w.temperature_c, w.precipitation_mm,
    COALESCE(c.is_public_holiday, false) AS ferie,
    COALESCE(c.is_school_holiday, false) AS vacances
FROM station_status ss
JOIN stations s USING (station_id)
LEFT JOIN weather w ON w.ts = date_trunc('hour', ss.ts)
LEFT JOIN calendar_days c ON c.day = ss.ts::date
ORDER BY ss.ts DESC
LIMIT 5;
```

### Volume de stockage estimé

Mesuré empiriquement sur les données déjà collectées (taille de table +
index via `hypertable_size()`) : **≈ 165 octets par ligne**. Avec 1522
stations interrogées toutes les 60s :

```
1522 stations × 1440 cycles/jour ≈ 2,19 millions de lignes/jour
2,19M lignes × 165 octets ≈ 345 Mo/jour (≈ 10 Go/mois)
```

Volume raisonnable pour TimescaleDB sur la durée du projet ; la
compression native TimescaleDB (`ALTER TABLE ... SET (timescaledb.compress)`)
pourra être activée plus tard sur les anciens chunks si besoin, sans
impact sur l'ingestion.

## Captures d'écran

Prises sur le build Docker (nginx, `http://localhost:3000`) le 2026-11-12,
avec des données réelles collectées en continu depuis la Phase 1. Design
revu en deux passes : identité visuelle (Phase 6 bis — typographie Inter/
Lexend, palette violette de marque distincte des couleurs d'état/données,
cartes avec ombres et coins arrondis, icônes lucide-react) puis finitions
UX (Phase 6 ter — mode sombre, menu mobile, squelettes de chargement,
états vides, accessibilité). Les couleurs qui encodent une donnée (état
de station, séries des graphiques) n'ont jamais changé, validées en
Phase 6.

| | |
|---|---|
| **Carte** — ~1522 stations, couleur + légende par état | **Carte filtrée** — `arrondissement=16e&velo=mecanique&etat=disponible`, combiné dans l'URL |
| ![Carte des stations](docs/screenshots/01-carte.jpg) | ![Carte avec filtres combinés](docs/screenshots/02-carte-filtres.jpg) |
| **Fiche station** — 24h + prédiction honnête quand l'historique récent manque | **Tableau de bord** — indicateurs globaux + 3 graphiques |
| ![Fiche station](docs/screenshots/03-fiche-station.jpg) | ![Tableau de bord](docs/screenshots/04-tableau-de-bord.jpg) |
| **À propos** — sources open data et attribution ODbL | **État d'erreur** — API arrêtée volontairement pour vérifier le message + bouton « Réessayer » |
| ![À propos](docs/screenshots/05-a-propos.jpg) | ![Erreur API injoignable](docs/screenshots/06-erreur-api.jpg) |
| **Mode sombre** — bascule mémorisée (localStorage), suit aussi la préférence système par défaut | |
| ![Tableau de bord en mode sombre](docs/screenshots/07-mode-sombre.jpg) | |

La fiche station ci-dessus illustre aussi le cas honnête d'une
prédiction indisponible (historique récent encore trop court pour cette
station) : l'API refuse de deviner plutôt que d'afficher un chiffre
inventé, message explicite à l'appui.

## État d'avancement

- [x] Phase 0 — Initialisation du dépôt (arborescence, Docker Compose,
      README)
- [x] Phase 1 — Collecte de données (producer GBFS → Kafka, référentiel
      stations, schéma TimescaleDB, archiver avec commit d'offsets après
      insertion)
- [x] Phase 2 — Enrichissement (météo Open-Meteo, jours fériés + vacances
      scolaires zone C, commune/arrondissement par station)
- [x] Phase 3 — Consumer temps réel → Redis, API FastAPI (4 endpoints,
      Swagger, tests pytest)
- [x] Phase 4 — Analyse de données et data viz (5 notebooks matplotlib, 5
      vues SQL + exports CSV pour Power BI)
- [x] Phase 5 — Modèle de prédiction (baselines, régression linéaire,
      LightGBM, SHAP, endpoint `/prediction`, script de ré-entraînement —
      voir [`ml/reports/RESULTATS.md`](ml/reports/RESULTATS.md))
- [x] Phase 6 — Web App (React + Vite + react-leaflet) : carte,
      recherche + filtres combinables reflétés dans l'URL, fiche station
      (historique, prédictions, risque en niveau discret), tableau de
      bord, page À propos avec attribution ODbL, états de chargement/
      erreur, frontend ajouté au `docker-compose.yml` — voir
      [Captures d'écran](#captures-décran)
- [x] Phase 7 (partiel) — Bonus Big Data : orchestration Airflow faite
      (enrichissement quotidien + réentraînement nocturne du modèle, voir
      [Airflow — orchestration](#airflow--orchestration-bonus-phase-7)) ;
      PySpark Structured Streaming pas encore fait

Chaque phase est validée avant de passer à la suivante (voir `CLAUDE.md`).
