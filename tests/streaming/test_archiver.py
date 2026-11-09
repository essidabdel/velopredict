import json

from streaming.archiver import parse_message


def _encode(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def test_parse_message_returns_expected_row():
    payload = {
        "station_id": 213688169,
        "station_code": "16107",
        "num_bikes_available": 14,
        "num_mechanical": 6,
        "num_ebike": 8,
        "num_docks_available": 20,
        "is_installed": True,
        "is_renting": True,
        "is_returning": True,
        "last_reported": 1700000000,
        "collected_at": "2026-11-09T18:00:00+00:00",
    }

    row = parse_message(_encode(payload), offset=42)

    assert row[0] == 213688169
    assert row[1] == "2026-11-09T18:00:00+00:00"
    assert row[3] == 6
    assert row[4] == 8
    assert row[5] == 20
    assert row[6] is True
    assert row[7] is True
    assert row[8] == "live"


def test_parse_message_returns_none_on_missing_field():
    payload = {"station_id": 1}  # champs requis manquants
    assert parse_message(_encode(payload), offset=1) is None


def test_parse_message_returns_none_on_invalid_json():
    assert parse_message(b"not-json", offset=1) is None
