import pandas as pd

from ml.baselines import (
    fit_historical_average,
    historical_average_predictions,
    persistence_predictions,
)


def test_persistence_predictions_repeats_current_value():
    df = pd.DataFrame({"bikes_t": [5, 10, 0]})
    result = persistence_predictions(df)
    assert list(result["bikes_t_plus_30"]) == [5, 10, 0]
    assert list(result["bikes_t_plus_60"]) == [5, 10, 0]


def test_fit_historical_average_groups_by_station_hour_weekday():
    train = pd.DataFrame(
        {
            "station_id": [1, 1, 1, 2],
            "heure": [8, 8, 9, 8],
            "jour_semaine": [0, 0, 0, 0],
            "bikes_t_plus_30": [10, 20, 5, 100],
            "bikes_t_plus_60": [12, 22, 6, 102],
        }
    )
    hist_avg = fit_historical_average(train)

    row = hist_avg[(hist_avg.station_id == 1) & (hist_avg.heure == 8)].iloc[0]
    assert row["hist_avg_bikes_t_plus_30"] == 15  # moyenne de 10 et 20
    assert row["hist_avg_bikes_t_plus_60"] == 17


def test_historical_average_predictions_falls_back_to_persistence_when_unseen():
    train = pd.DataFrame(
        {
            "station_id": [1],
            "heure": [8],
            "jour_semaine": [0],
            "bikes_t_plus_30": [10],
            "bikes_t_plus_60": [12],
        }
    )
    hist_avg = fit_historical_average(train)

    # station 2 jamais vue au train -> repli sur la persistance (bikes_t)
    test = pd.DataFrame({"station_id": [2], "heure": [8], "jour_semaine": [0], "bikes_t": [42]})
    predictions = historical_average_predictions(test, hist_avg)

    assert predictions["bikes_t_plus_30"].iloc[0] == 42
    assert predictions["bikes_t_plus_60"].iloc[0] == 42
