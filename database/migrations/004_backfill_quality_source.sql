-- VéloPredict — Phase 4/5 : traçabilité de la source des relevés et
-- qualité des jours backfillés depuis l'archive communautaire ODbL.

-- ---------------------------------------------------------------------
-- Colonne "source" sur station_status. DEFAULT 'live' pour que l'archiver
-- déjà en cours d'exécution (ancien code, INSERT sans cette colonne)
-- continue de fonctionner sans interruption jusqu'à son redémarrage avec
-- le code mis à jour — jamais casser la collecte en continu.
-- ---------------------------------------------------------------------
ALTER TABLE station_status
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'live';

-- Rattrapage pour les lignes déjà présentes avant l'ajout de la colonne :
-- frontière temporelle exacte connue entre l'archive backfillée
-- (tibzsecondaire/velib-data, jusqu'au 2026-11-08) et notre collecte
-- (démarrée le 2026-11-09 à 16:21:07 UTC) — aucun chevauchement.
UPDATE station_status
SET source = 'backfill_github'
WHERE ts < '2026-11-09 16:21:07.445857+00' AND source = 'live';

ALTER TABLE station_status
    ADD CONSTRAINT station_status_source_check CHECK (source IN ('live', 'backfill_github'));

CREATE INDEX IF NOT EXISTS idx_station_status_source ON station_status (source);

-- ---------------------------------------------------------------------
-- Qualité par jour de l'archive backfillée, dérivée de daily/index.csv
-- (tibzsecondaire/velib-data). "day" est un jour UTC (comme dans
-- l'archive source) — ne pas confondre avec un jour Europe/Paris lors
-- des jointures. Repeuplée à chaque exécution de ingestion/backfill.py.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS backfill_day_quality (
    day              DATE PRIMARY KEY,
    snapshots        INTEGER NOT NULL,
    max_gap_minutes  NUMERIC(10, 1) NOT NULL,
    reliable         BOOLEAN NOT NULL
);

-- ---------------------------------------------------------------------
-- Vue "prête pour l'entraînement" : toutes les lignes collectées en
-- direct (pas de trou documenté, on leur fait confiance) + les lignes
-- backfillées dont le jour UTC est "reliable" (max_gap_minutes <= 60,
-- voir ingestion/backfill.py). Exclut en pratique le 2026-10-26 et le
-- 2026-11-02 au 2026-11-08 de l'archive backfillée.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_training_eligible_status AS
SELECT ss.*
FROM station_status ss
LEFT JOIN backfill_day_quality q ON q.day = (ss.ts AT TIME ZONE 'UTC')::date
WHERE ss.source = 'live' OR q.reliable;
