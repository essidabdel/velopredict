-- VéloPredict — Phase 4 : vues d'agrégation pour l'analyse et Power BI.
-- Toutes les vues sont recalculées à la volée (pas de matérialisation) :
-- le volume de station_status reste gérable pour un projet scolaire, et
-- ça garantit des chiffres toujours à jour sans job de rafraîchissement.

-- ---------------------------------------------------------------------
-- 1) Disponibilité moyenne par heure de la journée, semaine vs week-end.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_hourly_availability AS
SELECT
    EXTRACT(HOUR FROM ts AT TIME ZONE 'Europe/Paris')::int AS heure,
    CASE
        WHEN EXTRACT(ISODOW FROM ts AT TIME ZONE 'Europe/Paris') IN (6, 7) THEN 'week-end'
        ELSE 'semaine'
    END AS jour_type,
    avg(num_mechanical)::numeric(10, 2) AS avg_mecanique,
    avg(num_ebike)::numeric(10, 2) AS avg_electrique,
    avg(num_mechanical + num_ebike)::numeric(10, 2) AS avg_velos_total,
    avg(num_docks_available)::numeric(10, 2) AS avg_bornes_libres,
    count(*) AS nb_mesures
FROM station_status
GROUP BY 1, 2;

-- ---------------------------------------------------------------------
-- 2) Flux domicile-travail par station : disponibilité moyenne le matin
-- (7h-9h) vs le soir (17h-19h), jours de semaine uniquement. Un flux_net
-- positif = la station se remplit le soir (typique d'une zone résidentielle,
-- les gens y ramènent des vélos en rentrant) ; négatif = elle se vide le
-- matin (typique d'une zone d'emploi, les gens y récupèrent des vélos).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_station_flux_domicile_travail AS
SELECT
    s.station_id,
    s.name,
    s.commune_nom,
    s.lat,
    s.lon,
    s.capacity,
    avg(
        CASE WHEN EXTRACT(HOUR FROM ss.ts AT TIME ZONE 'Europe/Paris') BETWEEN 7 AND 9
             THEN ss.num_mechanical + ss.num_ebike END
    )::numeric(10, 2) AS avg_velos_matin,
    avg(
        CASE WHEN EXTRACT(HOUR FROM ss.ts AT TIME ZONE 'Europe/Paris') BETWEEN 17 AND 19
             THEN ss.num_mechanical + ss.num_ebike END
    )::numeric(10, 2) AS avg_velos_soir
FROM station_status ss
JOIN stations s USING (station_id)
WHERE EXTRACT(ISODOW FROM ss.ts AT TIME ZONE 'Europe/Paris') NOT IN (6, 7)
GROUP BY s.station_id, s.name, s.commune_nom, s.lat, s.lon, s.capacity;

-- ---------------------------------------------------------------------
-- 3) Mouvement horaire (proxy d'usage) + météo. Le flux GBFS ne donne que
-- des photographies de stock (vélos présents), pas le nombre de trajets :
-- on approxime l'usage par la somme des variations absolues de stock
-- d'une mesure à l'autre (plus ça bouge, plus il y a de location/retour).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_hourly_movement_weather AS
WITH deltas AS (
    SELECT
        station_id,
        ts,
        (num_mechanical + num_ebike)
            - LAG(num_mechanical + num_ebike) OVER (PARTITION BY station_id ORDER BY ts) AS delta
    FROM station_status
),
mouvement_horaire AS (
    SELECT date_trunc('hour', ts) AS heure, sum(abs(delta)) AS mouvement_total
    FROM deltas
    WHERE delta IS NOT NULL
    GROUP BY 1
)
SELECT
    mh.heure,
    mh.mouvement_total,
    w.temperature_c,
    w.precipitation_mm,
    w.wind_speed_kmh
FROM mouvement_horaire mh
LEFT JOIN weather w ON w.ts = mh.heure
ORDER BY mh.heure;

-- ---------------------------------------------------------------------
-- 4) Comparaison vélos mécaniques vs électriques, heure par heure.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_bike_type_share AS
SELECT
    date_trunc('hour', ts) AS heure,
    avg(num_mechanical)::numeric(10, 2) AS avg_mecanique,
    avg(num_ebike)::numeric(10, 2) AS avg_electrique,
    (sum(num_mechanical)::float / NULLIF(sum(num_mechanical + num_ebike), 0))::numeric(5, 4)
        AS part_mecanique
FROM station_status
GROUP BY 1
ORDER BY 1;

-- ---------------------------------------------------------------------
-- 5) Taux de pénurie (stations à 0 vélo disponible) par commune/arrondissement.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_penurie_par_commune AS
SELECT
    s.commune_nom,
    count(*) AS nb_mesures,
    sum(CASE WHEN (ss.num_mechanical + ss.num_ebike) = 0 THEN 1 ELSE 0 END) AS nb_mesures_vide,
    (
        sum(CASE WHEN (ss.num_mechanical + ss.num_ebike) = 0 THEN 1 ELSE 0 END)::float
        / count(*)
    )::numeric(5, 4) AS taux_penurie
FROM station_status ss
JOIN stations s USING (station_id)
WHERE s.commune_nom IS NOT NULL
GROUP BY s.commune_nom
ORDER BY taux_penurie DESC;
