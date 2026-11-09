from ingestion.producer import build_message, extract_bike_types


def test_extract_bike_types_sums_known_keys():
    types = [{"mechanical": 6}, {"ebike": 8}]
    assert extract_bike_types(types) == (6, 8)


def test_extract_bike_types_handles_missing_or_empty():
    assert extract_bike_types(None) == (0, 0)
    assert extract_bike_types([]) == (0, 0)
    assert extract_bike_types([{"ebike": 3}]) == (0, 3)


def test_build_message_flattens_real_gbfs_shape():
    station = {
        "station_id": 213688169,
        "stationCode": "16107",
        "num_bikes_available": 14,
        "num_bikes_available_types": [{"mechanical": 6}, {"ebike": 8}],
        "num_docks_available": 20,
        "is_installed": 1,
        "is_returning": 1,
        "is_renting": 1,
        "last_reported": 1700000000,
        "station_opening_hours": None,
    }
    message = build_message(station, collected_at="2026-11-09T18:00:00+00:00")

    assert message["station_id"] == 213688169
    assert message["station_code"] == "16107"
    assert message["num_mechanical"] == 6
    assert message["num_ebike"] == 8
    assert message["num_docks_available"] == 20
    assert message["is_renting"] is True
    assert message["is_returning"] is True
    assert message["is_installed"] is True
    assert message["last_reported"] == 1700000000
    assert message["collected_at"] == "2026-11-09T18:00:00+00:00"
