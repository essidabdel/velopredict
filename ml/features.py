"""Construction du jeu de données ML : variables listées dans CLAUDE.md,
cibles à t+30 et t+60 (nombre total de vélos disponibles).

Méthode de ré-échantillonnage : les relevés bruts (station_status) sont
irréguliers (60s pour notre collecte, ~5min avec trous pour l'archive
backfillée). On les projette sur une grille fixe de 15 minutes par
station via un rapprochement "au plus proche" (`merge_asof`,
`direction="nearest"`) borné à 30 minutes de tolérance : au-delà, on ne
comble pas le trou (valeur manquante), plutôt que d'inventer une donnée.

Lags et cibles : calculés par **jointure explicite sur l'horodatage réel**
(`ts ± offset`), pas par décalage de lignes (`shift`). Un `shift()`
suppose silencieusement que la grille est parfaitement régulière (une
ligne toutes les 15 min, sans trou) — vrai par construction ici, mais
fragile : si une station manquait une portion de grille, ou si le filtre
des stations inactives (voir `filter_active_stations`) retirait des lignes
avant ce calcul, un `shift()` positionnel donnerait silencieusement la
mauvaise valeur. La jointure sur `station_id` + horodatage exact est
correcte indépendamment de ces conditions — voir `_join_on_timestamp`.

Stations inactives : les relevés avec `is_renting = 0` (station fermée,
maintenance...) ou un `last_reported` trop ancien (station qui ne répond
plus au flux GBFS) sont retirés avant le calcul des lags/cibles — ni comme
feature (on ne prédit pas depuis un état fermé), ni comme cible (on ne
prédit pas vers un état fermé).

Fuseau horaire : tous les horodatages en base sont en UTC. Les variables
calendaires (heure, jour de semaine, jour férié, vacances scolaires) sont
calculées après conversion en Europe/Paris via `zoneinfo` (et non un
décalage fixe), pour gérer correctement le changement d'heure du
2026-10-25 présent dans la fenêtre d'entraînement.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy.engine import Engine

PARIS_TZ = ZoneInfo("Europe/Paris")
GRID_FREQ = "15min"
TOLERANCE = pd.Timedelta("30min")

# Un relevé est considéré inactif si last_reported est plus vieux que ça
# par rapport à l'horodatage de collecte (ts) : la station ne répond plus
# vraiment au flux GBFS (hors service, retirée...).
STALE_THRESHOLD = pd.Timedelta("2h")

FEATURE_COLUMNS = [
    "heure",
    "jour_semaine",
    "is_weekend",
    "is_public_holiday",
    "is_school_holiday",
    "temperature_c",
    "precipitation_mm",
    "wind_speed_kmh",
    "bikes_t",
    "bikes_t_minus_15",
    "bikes_t_minus_30",
    "bikes_t_minus_60",
    "docks_t",
    "capacity",
    "lat",
    "lon",
]
TARGET_COLUMNS = ["bikes_t_plus_30", "bikes_t_plus_60"]
ID_COLUMNS = ["station_id", "ts"]


def load_stations(engine: Engine) -> pd.DataFrame:
    return pd.read_sql("SELECT station_id, capacity, lat, lon FROM stations", engine)


def load_weather(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT ts, temperature_c, precipitation_mm, wind_speed_kmh FROM weather",
        engine,
        parse_dates=["ts"],
    )


def load_calendar(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT day, is_public_holiday, is_school_holiday FROM calendar_days",
        engine,
        parse_dates=["day"],
    )


def load_raw_status(
    engine: Engine,
    start: datetime,
    end: datetime,
    include_unreliable: bool = False,
    source_filter: str | None = None,
) -> pd.DataFrame:
    """Relevés bruts sur [start, end). Par défaut limités aux jours jugés
    fiables (v_training_eligible_status — voir ingestion/backfill.py).
    `include_unreliable=True` lit directement station_status (ignore le
    filtre de fiabilité) — utilisé ponctuellement pour évaluer des jours
    exclus par défaut (ex: 2026-11-02/03, voir ml/reports/RESULTATS.md).
    `source_filter` restreint explicitement à 'live' ou 'backfill_github'
    (utilisé par ml/evaluate_live.py pour ne jamais mélanger les deux,
    même si les fenêtres de temps ne se recoupent pas en pratique).
    Inclut is_renting/last_reported pour le filtrage des stations
    inactives, appliqué plus tard par filter_active_stations."""
    table = "station_status" if include_unreliable else "v_training_eligible_status"
    source_clause = " AND source = %(source_filter)s" if source_filter else ""
    return pd.read_sql(
        f"""
        SELECT station_id, ts, num_mechanical, num_ebike, num_docks_available,
               is_renting, last_reported
        FROM {table}
        WHERE ts >= %(start)s AND ts < %(end)s{source_clause}
        """,  # noqa: S608 - table/clause restreints à des valeurs internes fixes
        engine,
        params={"start": start, "end": end, "source_filter": source_filter},
        parse_dates=["ts", "last_reported"],
    )


def build_grid(station_ids: list[int], start: datetime, end: datetime) -> pd.DataFrame:
    grid_times = pd.date_range(start, end, freq=GRID_FREQ, tz="UTC", inclusive="left")
    index = pd.MultiIndex.from_product([station_ids, grid_times], names=["station_id", "ts"])
    return index.to_frame(index=False)


def resample_nearest(raw: pd.DataFrame, grid: pd.DataFrame) -> pd.DataFrame:
    raw_sorted = raw.sort_values(["ts", "station_id"])
    grid_sorted = grid.sort_values(["ts", "station_id"])
    merged = pd.merge_asof(
        grid_sorted,
        raw_sorted,
        on="ts",
        by="station_id",
        direction="nearest",
        tolerance=TOLERANCE,
    )
    return merged.sort_values(["station_id", "ts"]).reset_index(drop=True)


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    local = df["ts"].dt.tz_convert(PARIS_TZ)
    df["heure"] = local.dt.hour
    df["jour_semaine"] = local.dt.dayofweek
    df["is_weekend"] = (df["jour_semaine"] >= 5).astype(int)
    df["_local_date"] = local.dt.tz_localize(None).dt.normalize()
    return df


def add_calendar_features(df: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(calendar, left_on="_local_date", right_on="day", how="left")
    df["is_public_holiday"] = df["is_public_holiday"].astype("boolean").fillna(False).astype(int)
    df["is_school_holiday"] = df["is_school_holiday"].astype("boolean").fillna(False).astype(int)
    return df.drop(columns=["_local_date", "day"])


def add_weather_features(df: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    df["_hour_utc"] = df["ts"].dt.floor("h")
    df = df.merge(
        weather, left_on="_hour_utc", right_on="ts", how="left", suffixes=("", "_weather")
    )
    return df.drop(columns=["_hour_utc", "ts_weather"], errors="ignore")


def add_station_features(df: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    return df.merge(stations, on="station_id", how="left")


def filter_active_stations(df: pd.DataFrame) -> pd.DataFrame:
    """Ne garde que les relevés de stations actives : is_renting=1 et un
    last_reported pas plus vieux que STALE_THRESHOLD par rapport à ts.
    Un relevé sans correspondance dans la tolérance de resample_nearest
    (is_renting/last_reported à NaN) est traité comme inactif."""
    is_renting = df["is_renting"].astype("boolean").fillna(False)
    fresh = (df["ts"] - df["last_reported"]) <= STALE_THRESHOLD
    active = (is_renting & fresh.fillna(False)).to_numpy()
    return df[active].reset_index(drop=True)


def _join_on_timestamp(df: pd.DataFrame, offset_minutes: int, column_name: str) -> pd.DataFrame:
    """Jointure explicite sur l'horodatage réel ts + offset (station_id,
    horodatage exact), pas un décalage de lignes — voir la note en tête
    de module. `offset_minutes` positif = cible dans le futur (t+h),
    négatif = lag dans le passé (t-h)."""
    lookup = df[["station_id", "ts", "bikes"]].rename(
        columns={"ts": "_lookup_ts", "bikes": column_name}
    )
    df = df.copy()
    df["_lookup_ts"] = df["ts"] + pd.Timedelta(minutes=offset_minutes)
    df = df.merge(lookup, on=["station_id", "_lookup_ts"], how="left")
    return df.drop(columns=["_lookup_ts"])


def add_lags_and_targets(df: pd.DataFrame) -> pd.DataFrame:
    df["bikes"] = df["num_mechanical"] + df["num_ebike"]
    df["bikes_t"] = df["bikes"]
    df["docks_t"] = df["num_docks_available"]

    for offset_minutes, column_name in (
        (-15, "bikes_t_minus_15"),
        (-30, "bikes_t_minus_30"),
        (-60, "bikes_t_minus_60"),
        (30, "bikes_t_plus_30"),
        (60, "bikes_t_plus_60"),
    ):
        df = _join_on_timestamp(df, offset_minutes, column_name)

    return df


def build_feature_table(
    engine: Engine,
    start: datetime,
    end: datetime,
    include_unreliable: bool = False,
    source_filter: str | None = None,
) -> pd.DataFrame:
    """Construit la table de features + cibles complète sur [start, end).
    Ne garde que les lignes où toutes les features et cibles requises
    sont renseignées (pas d'imputation : on préfère perdre une ligne que
    deviner une valeur). `include_unreliable`/`source_filter` : voir
    load_raw_status."""
    stations = load_stations(engine)
    weather = load_weather(engine)
    calendar = load_calendar(engine)
    raw = load_raw_status(
        engine, start, end, include_unreliable=include_unreliable, source_filter=source_filter
    )

    station_ids = stations["station_id"].tolist()
    grid = build_grid(station_ids, start, end)
    df = resample_nearest(raw, grid)
    df = filter_active_stations(df)

    df = add_lags_and_targets(df)
    df = add_time_features(df)
    df = add_calendar_features(df, calendar)
    df = add_weather_features(df, weather)
    df = add_station_features(df, stations)

    required = ID_COLUMNS + FEATURE_COLUMNS + TARGET_COLUMNS
    df = df.dropna(subset=required).reset_index(drop=True)
    return df[required]
