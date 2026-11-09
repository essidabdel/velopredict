-- VéloPredict — schéma initial
-- Appliqué automatiquement au premier démarrage de TimescaleDB via
-- docker-entrypoint-initdb.d (voir docker-compose.yml).

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------
-- Référentiel des stations, chargé par ingestion/stations.py depuis
-- station_information.json. Volontairement SANS clé étrangère depuis
-- station_status : l'archiver doit pouvoir insérer l'historique même si
-- le référentiel n'a pas encore été chargé (ou a été rechargé), pour ne
-- jamais perdre de données de collecte.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stations (
    station_id   BIGINT PRIMARY KEY,
    station_code TEXT NOT NULL,
    name         TEXT NOT NULL,
    lat          DOUBLE PRECISION NOT NULL,
    lon          DOUBLE PRECISION NOT NULL,
    capacity     SMALLINT NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_stations_station_code ON stations (station_code);

-- ---------------------------------------------------------------------
-- Historique des relevés de disponibilité (hypertable TimescaleDB).
--
-- "ts"            = horodatage de collecte côté producer (collected_at),
--                   utilisé comme dimension de partitionnement temporel.
-- "last_reported" = horodatage du relevé tel que rapporté par le flux
--                   GBFS Vélib' (peut être identique entre deux cycles si
--                   le flux source n'a pas changé), conservé à part pour
--                   les features ML et la détection de flux figés.
--
-- PRIMARY KEY (station_id, ts) sert à la fois d'index principal et de
-- contrainte d'unicité anti-doublon : si l'archiver retraite les mêmes
-- messages Kafka après un redémarrage avant d'avoir commité ses offsets,
-- l'insertion est simplement ignorée (ON CONFLICT DO NOTHING côté
-- archiver) au lieu de dupliquer la ligne.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS station_status (
    station_id          BIGINT NOT NULL,
    ts                   TIMESTAMPTZ NOT NULL,
    last_reported        TIMESTAMPTZ NOT NULL,
    num_mechanical       SMALLINT NOT NULL,
    num_ebike            SMALLINT NOT NULL,
    num_docks_available  SMALLINT NOT NULL,
    is_renting           BOOLEAN NOT NULL,
    is_returning         BOOLEAN NOT NULL,
    PRIMARY KEY (station_id, ts)
);

SELECT create_hypertable(
    'station_status',
    'ts',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Index "espace-temps" recommandé par Timescale pour les requêtes du
-- type "derniers relevés d'une station" (utilisées par l'API et le ML).
CREATE INDEX IF NOT EXISTS idx_station_status_station_ts
    ON station_status (station_id, ts DESC);
