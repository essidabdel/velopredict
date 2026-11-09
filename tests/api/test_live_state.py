import json

from api.live_state import (
    ETAT_DISPONIBLE,
    ETAT_INCONNU,
    ETAT_PLEINE,
    ETAT_VIDE,
    classify_state,
    fetch_all_live_station_ids,
    fetch_live_statuses,
)


def test_classify_state_unknown_when_no_live_data():
    assert classify_state(None) == ETAT_INCONNU


def test_classify_state_vide_when_no_bikes():
    assert (
        classify_state({"num_mechanical": 0, "num_ebike": 0, "num_docks_available": 5}) == ETAT_VIDE
    )


def test_classify_state_pleine_when_no_docks():
    assert (
        classify_state({"num_mechanical": 3, "num_ebike": 0, "num_docks_available": 0})
        == ETAT_PLEINE
    )


def test_classify_state_disponible_otherwise():
    assert (
        classify_state({"num_mechanical": 2, "num_ebike": 1, "num_docks_available": 4})
        == ETAT_DISPONIBLE
    )


def test_classify_state_vide_has_priority_over_pleine():
    # 0 vélo ET 0 borne (capacité nulle ou glitch) : on considère "vide" en priorité
    assert (
        classify_state({"num_mechanical": 0, "num_ebike": 0, "num_docks_available": 0}) == ETAT_VIDE
    )


class FakeRedis:
    def __init__(self, store: dict[str, str], index: set[str]):
        self.store = store
        self.index = index

    def mget(self, keys):
        return [self.store.get(key) for key in keys]

    def smembers(self, _key):
        return self.index


def test_fetch_live_statuses_parses_known_stations_and_skips_missing():
    store = {
        "station:1": json.dumps({"num_mechanical": 2, "num_ebike": 1, "num_docks_available": 3})
    }
    client = FakeRedis(store, set())

    result = fetch_live_statuses(client, [1, 2])

    assert result == {1: {"num_mechanical": 2, "num_ebike": 1, "num_docks_available": 3}}


def test_fetch_live_statuses_empty_input_returns_empty_dict():
    assert fetch_live_statuses(FakeRedis({}, set()), []) == {}


def test_fetch_all_live_station_ids_converts_to_int():
    client = FakeRedis({}, {"1", "2", "42"})
    assert sorted(fetch_all_live_station_ids(client)) == [1, 2, 42]
