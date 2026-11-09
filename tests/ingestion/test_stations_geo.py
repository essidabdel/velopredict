from ingestion.stations_geo import pick_result


def test_pick_result_prefers_arrondissement():
    arrondissements = [{"code": "75116", "nom": "Paris 16e Arrondissement"}]
    communes = [{"code": "75056", "nom": "Paris"}]
    assert pick_result(arrondissements, communes) == ("75116", "Paris 16e Arrondissement")


def test_pick_result_falls_back_to_commune():
    assert pick_result([], [{"code": "92044", "nom": "Levallois-Perret"}]) == (
        "92044",
        "Levallois-Perret",
    )


def test_pick_result_none_when_nothing_found():
    assert pick_result([], []) is None
