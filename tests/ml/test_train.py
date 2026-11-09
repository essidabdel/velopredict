import pandas as pd

from ml.train import temporal_split


def test_temporal_split_keeps_test_strictly_after_train():
    ts = pd.date_range("2026-10-01", periods=10, freq="D", tz="UTC")
    df = pd.DataFrame({"ts": ts, "value": range(10)})

    train, test = temporal_split(df, test_fraction=0.3)

    assert train["ts"].max() < test["ts"].min()
    assert len(train) + len(test) == len(df)


def test_temporal_split_keeps_same_timestamp_rows_together():
    # Plusieurs stations partagent le même horodatage : elles ne doivent
    # jamais être séparées entre train et test (sinon fuite partielle).
    ts = pd.to_datetime(["2026-10-01", "2026-10-01", "2026-10-02", "2026-10-02"], utc=True)
    df = pd.DataFrame({"ts": ts, "station_id": [1, 2, 1, 2]})

    train, test = temporal_split(df, test_fraction=0.5)

    assert set(train["ts"].unique()).isdisjoint(set(test["ts"].unique()))
