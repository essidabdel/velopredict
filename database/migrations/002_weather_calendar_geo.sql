-- VéloPredict — Phase 2 : enrichissement (météo, calendrier, géo stations)

-- ---------------------------------------------------------------------
-- Météo horaire pour Paris (point fixe lat/lon, cf. CLAUDE.md — la météo
-- est une variable globale, pas par station).
--
-- "source" distingue 'archive' (relevé historique Open-Meteo, considéré
-- définitif) de 'forecast' (prévision, provisoire). Voir la contrainte
-- d'upsert dans ingestion/weather.py : une prévision ne peut jamais
-- écraser un relevé archive déjà confirmé pour la même heure, mais
-- l'archive peut toujours remplacer une prévision une fois disponible.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather (
    ts                TIMESTAMPTZ PRIMARY KEY,
    temperature_c     REAL,
    precipitation_mm  REAL,
    wind_speed_kmh    REAL,
    source            TEXT NOT NULL CHECK (source IN ('archive', 'forecast')),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Calendrier (un jour = une ligne), alimenté indépendamment par deux
-- scripts : ingestion/calendar_days.py met à jour soit les colonnes
-- "public_holiday", soit les colonnes "school_holiday", sans jamais
-- écraser l'autre moitié de la ligne (upsert à colonnes disjointes).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS calendar_days (
    day                   DATE PRIMARY KEY,
    is_public_holiday     BOOLEAN NOT NULL DEFAULT FALSE,
    holiday_name          TEXT,
    is_school_holiday     BOOLEAN NOT NULL DEFAULT FALSE,
    school_holiday_name   TEXT
);

-- ---------------------------------------------------------------------
-- Enrichissement du référentiel stations : commune (ou arrondissement
-- pour Paris/Lyon/Marseille) déduite des coordonnées via geo.api.gouv.fr.
-- Rempli par ingestion/stations_geo.py (UPDATE uniquement, jamais
-- d'INSERT : pas de risque de doublon).
-- ---------------------------------------------------------------------
ALTER TABLE stations ADD COLUMN IF NOT EXISTS commune_code TEXT;
ALTER TABLE stations ADD COLUMN IF NOT EXISTS commune_nom TEXT;

CREATE INDEX IF NOT EXISTS idx_stations_commune_code ON stations (commune_code);
