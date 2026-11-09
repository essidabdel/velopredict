"""Enrichit la table `stations` avec la commune (ou l'arrondissement pour
Paris/Lyon/Marseille) déduite des coordonnées, via l'API officielle
geo.api.gouv.fr (reverse-geocoding par point). Relançable sans créer de
doublon : c'est toujours un UPDATE sur station_id, jamais un INSERT. Par
défaut, seules les stations sans commune_code sont interrogées ; `--refresh`
force une ré-interrogation complète.

La recherche "commune standard" (sans filtre d'arrondissement) de cette API
est intrinsèquement lente côté serveur (1 à 8s par appel, mesuré
empiriquement — la variante `type=arrondissement-municipal`, elle, répond
en <0,1s). Comme l'essentiel du temps est de l'attente réseau et non du
calcul, les requêtes sont parallélisées (threads) plutôt que ralenties par
un `sleep` séquentiel ; l'accès à la base reste entièrement dans le thread
principal (psycopg2 n'est pas thread-safe sur une connexion partagée).
"""

from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2

from . import config
from .http_utils import fetch_json_with_retry

logger = logging.getLogger("ingestion.stations_geo")

DEFAULT_WORKERS = 10
GEO_API_TIMEOUT = 20.0
COMMIT_EVERY = 100


def pick_result(arrondissements: list[dict], communes: list[dict]) -> tuple[str, str] | None:
    """Préfère l'arrondissement municipal (Paris/Lyon/Marseille) quand il
    existe, sinon la commune standard."""
    candidates = arrondissements or communes
    if not candidates:
        return None
    return candidates[0]["code"], candidates[0]["nom"]


def resolve_commune(lat: float, lon: float) -> tuple[str, str] | None:
    arrondissements = fetch_json_with_retry(
        config.GEO_API_BASE_URL,
        logger=logger,
        label="geo.api.gouv.fr (arrondissement)",
        max_attempts=5,
        timeout=GEO_API_TIMEOUT,
        params={
            "lat": lat,
            "lon": lon,
            "type": "arrondissement-municipal",
            "fields": "nom,code",
            "format": "json",
        },
    )
    if arrondissements:
        return pick_result(arrondissements, [])

    communes = fetch_json_with_retry(
        config.GEO_API_BASE_URL,
        logger=logger,
        label="geo.api.gouv.fr (commune)",
        max_attempts=5,
        timeout=GEO_API_TIMEOUT,
        params={"lat": lat, "lon": lon, "fields": "nom,code", "format": "json"},
    )
    return pick_result([], communes)


def fetch_stations_to_enrich(
    conn: psycopg2.extensions.connection, refresh: bool
) -> list[tuple[int, float, float]]:
    query = "SELECT station_id, lat, lon FROM stations"
    if not refresh:
        query += " WHERE commune_code IS NULL"
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


def enrich_stations(refresh: bool = False, workers: int = DEFAULT_WORKERS) -> int:
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL n'est pas défini (voir .env)")

    conn = psycopg2.connect(config.DATABASE_URL)
    try:
        stations = fetch_stations_to_enrich(conn, refresh)
        total = len(stations)
        logger.info("%d station(s) à géocoder (%d requêtes en parallèle)", total, workers)

        updated = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_station = {
                pool.submit(resolve_commune, lat, lon): station_id
                for station_id, lat, lon in stations
            }
            for done, future in enumerate(as_completed(future_to_station), start=1):
                station_id = future_to_station[future]
                try:
                    result = future.result()
                except Exception:
                    logger.exception("Échec du géocodage de la station %s", station_id)
                    continue

                if result is None:
                    logger.warning("Aucune commune trouvée pour la station %s", station_id)
                    continue

                commune_code, commune_nom = result
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE stations SET commune_code = %s, commune_nom = %s "
                        "WHERE station_id = %s",
                        (commune_code, commune_nom, station_id),
                    )
                updated += 1
                if updated % COMMIT_EVERY == 0:
                    conn.commit()
                    logger.info(
                        "%d/%d station(s) traitées, %d mises à jour (commit intermédiaire)",
                        done,
                        total,
                        updated,
                    )

        conn.commit()
        logger.info("%d/%d station(s) mises à jour au total", updated, total)
        return updated
    finally:
        conn.close()


def main() -> None:
    logging.basicConfig(
        level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-géocoder aussi les stations qui ont déjà une commune renseignée",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Nombre de requêtes HTTP en parallèle (défaut: {DEFAULT_WORKERS})",
    )
    args = parser.parse_args()
    enrich_stations(refresh=args.refresh, workers=args.workers)


if __name__ == "__main__":
    main()
