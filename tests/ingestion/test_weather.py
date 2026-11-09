from datetime import UTC, datetime

from ingestion.weather import rows_from_payload


def test_rows_from_payload_converts_paris_local_time_to_utc():
    payload = {
        "hourly": {
            "time": ["2026-11-09T00:00", "2026-11-09T01:00"],
            "temperature_2m": [6.8, 6.6],
            "precipitation": [0.0, 0.1],
            "wind_speed_10m": [6.6, 5.9],
        }
    }

    rows = rows_from_payload(payload, source="forecast")

    assert len(rows) == 2
    ts0, temp0, precip0, wind0, source0 = rows[0]
    # Paris est en UTC+1 en novembre (heure d'hiver)
    assert ts0.astimezone(UTC) == datetime(2026, 11, 8, 23, 0, tzinfo=UTC)
    assert temp0 == 6.8
    assert precip0 == 0.0
    assert wind0 == 6.6
    assert source0 == "forecast"


def test_rows_from_payload_empty_hourly_returns_no_rows():
    payload = {
        "hourly": {"time": [], "temperature_2m": [], "precipitation": [], "wind_speed_10m": []}
    }
    assert rows_from_payload(payload, source="archive") == []
