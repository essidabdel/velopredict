import json

from streaming.live import parse_message


def test_parse_message_returns_payload_dict():
    payload = {"station_id": 213688169, "num_mechanical": 6, "num_ebike": 8}
    result = parse_message(json.dumps(payload).encode("utf-8"))
    assert result == payload


def test_parse_message_returns_none_on_missing_station_id():
    assert parse_message(json.dumps({"num_mechanical": 6}).encode("utf-8")) is None


def test_parse_message_returns_none_on_invalid_json():
    assert parse_message(b"not-json") is None
