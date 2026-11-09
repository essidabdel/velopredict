import pandas as pd

from ml.features import add_lags_and_targets, add_time_features, filter_active_stations


def test_add_time_features_handles_dst_fallback_2026_10_25():
    # Le passage heure d'été -> heure d'hiver a lieu a 01:00 UTC le
    # 2026-10-25 (03:00 CEST -> 02:00 CET). Avant : Paris = UTC+2.
    # Apres : Paris = UTC+1.
    ts = pd.to_datetime(["2026-10-25 00:30:00+00:00", "2026-10-25 02:00:00+00:00"], utc=True)
    df = pd.DataFrame({"ts": ts})

    result = add_time_features(df)

    assert result["heure"].iloc[0] == 2  # 00:30 UTC -> 02:30 CEST (avant le changement)
    assert result["heure"].iloc[1] == 3  # 02:00 UTC -> 03:00 CET (apres le changement)


def test_add_time_features_weekend_flag():
    # 2026-11-07 est un samedi, 2026-11-09 un lundi
    ts = pd.to_datetime(["2026-11-07 12:00:00+00:00", "2026-11-09 12:00:00+00:00"], utc=True)
    df = pd.DataFrame({"ts": ts})

    result = add_time_features(df)

    assert result["is_weekend"].iloc[0] == 1
    assert result["is_weekend"].iloc[1] == 0


def test_add_lags_and_targets_uses_real_timestamp_not_row_position():
    # Grille avec un trou : pas de relevé à 00:30 pour la station 1. Un
    # shift() positionnel donnerait une valeur fausse pour la cible à
    # t+30 de la ligne 00:00 (il prendrait la ligne suivante, 00:45, au
    # lieu de NaN) ; une jointure sur l'horodatage réel donne NaN.
    df = pd.DataFrame(
        {
            "station_id": [1, 1, 1, 1],
            "ts": pd.to_datetime(
                ["2026-10-10 00:00", "2026-10-10 00:15", "2026-10-10 00:45", "2026-10-10 01:00"],
                utc=True,
            ),
            "num_mechanical": [6, 7, 8, 9],
            "num_ebike": [4, 4, 5, 5],
            "num_docks_available": [10, 10, 10, 10],
        }
    )

    result = add_lags_and_targets(df).set_index("ts")

    # ligne 00:00 : t+30 = 00:30, absente de la grille -> NaN, pas la
    # valeur de la ligne suivante (00:45, qui vaut 13)
    assert pd.isna(result.loc[pd.Timestamp("2026-10-10 00:00", tz="UTC"), "bikes_t_plus_30"])

    # ligne 00:15 : t+30 = 00:45, présente (bikes = 8+5 = 13)
    assert result.loc[pd.Timestamp("2026-10-10 00:15", tz="UTC"), "bikes_t_plus_30"] == 13

    # ligne 01:00 : t-15 = 00:45, présente (bikes = 13)
    assert result.loc[pd.Timestamp("2026-10-10 01:00", tz="UTC"), "bikes_t_minus_15"] == 13

    # ligne 00:45 : t-15 = 00:30, absente -> NaN (pas la valeur de 00:15)
    assert pd.isna(result.loc[pd.Timestamp("2026-10-10 00:45", tz="UTC"), "bikes_t_minus_15"])


def test_filter_active_stations_removes_not_renting():
    df = pd.DataFrame(
        {
            "station_id": [1, 2, 3],
            "is_renting": [True, False, True],
            "last_reported": pd.to_datetime(["2026-10-10 00:00"] * 3, utc=True),
            "ts": pd.to_datetime(["2026-10-10 00:05"] * 3, utc=True),
        }
    )

    result = filter_active_stations(df)

    assert sorted(result["station_id"].tolist()) == [1, 3]


def test_filter_active_stations_removes_stale_last_reported():
    df = pd.DataFrame(
        {
            "station_id": [1, 2],
            "is_renting": [True, True],
            # station 2 : last_reported vieux de 4h -> au-delà de STALE_THRESHOLD (2h)
            "last_reported": pd.to_datetime(["2026-10-10 00:00", "2026-10-09 20:00"], utc=True),
            "ts": pd.to_datetime(["2026-10-10 00:05", "2026-10-10 00:05"], utc=True),
        }
    )

    result = filter_active_stations(df)

    assert result["station_id"].tolist() == [1]
