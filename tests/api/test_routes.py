def test_list_stations_returns_all_by_default(client):
    response = client.get("/stations")
    assert response.status_code == 200
    body = response.json()
    assert {s["station_id"] for s in body} == {1, 2, 3}


def test_list_stations_filters_by_arrondissement(client):
    response = client.get("/stations", params={"arrondissement": "16e"})
    assert response.status_code == 200
    body = response.json()
    assert [s["station_id"] for s in body] == [1]


def test_list_stations_filters_by_recherche(client):
    response = client.get("/stations", params={"recherche": "levallois"})
    assert response.status_code == 200
    assert [s["station_id"] for s in response.json()] == [2]


def test_list_stations_filters_by_etat_vide(client):
    response = client.get("/stations", params={"etat": "vide"})
    assert response.status_code == 200
    # station 2 a 0 vélo -> "vide" ; station 3 n'a pas d'état -> "inconnue" (exclue)
    assert [s["station_id"] for s in response.json()] == [2]


def test_list_stations_filters_by_velo_type(client):
    response = client.get("/stations", params={"velo": "electrique"})
    assert response.status_code == 200
    # seule la station 1 a des vélos électriques disponibles (8)
    assert [s["station_id"] for s in response.json()] == [1]


def test_get_station_detail(client):
    response = client.get("/stations/1")
    assert response.status_code == 200
    body = response.json()
    assert body["station_id"] == 1
    assert body["etat"] == "disponible"
    assert body["num_ebike"] == 8
    assert body["collected_at"] == "2026-11-09T18:00:00+00:00"


def test_get_station_detail_unknown_live_state(client):
    response = client.get("/stations/3")
    assert response.status_code == 200
    body = response.json()
    assert body["etat"] == "inconnue"
    assert body["num_mechanical"] is None


def test_get_station_detail_404_when_missing(client):
    response = client.get("/stations/999")
    assert response.status_code == 404


def test_get_station_history(client):
    response = client.get("/stations/1/history", params={"hours": 24})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[-1]["num_ebike"] == 8


def test_get_station_history_404_when_station_missing(client):
    response = client.get("/stations/999/history")
    assert response.status_code == 404


def test_get_station_history_rejects_out_of_range_hours(client):
    response = client.get("/stations/1/history", params={"hours": 999})
    assert response.status_code == 422


def test_stats_overview(client):
    response = client.get("/stats/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["nb_stations"] == 3
    assert body["nb_stations_avec_etat"] == 2
    assert body["total_mechanical"] == 6
    assert body["total_ebike"] == 8
    assert body["nb_stations_vides"] == 1
    assert body["nb_stations_pleines"] == 0


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
