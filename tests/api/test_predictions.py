import api.routers.predictions as predictions_module


def test_prediction_success(client, monkeypatch, tmp_path):
    (tmp_path / "lightgbm_30.joblib").write_text("fake")
    monkeypatch.setattr(predictions_module, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(
        predictions_module,
        "predict_station",
        lambda engine, station_id: {
            "station_id": station_id,
            "as_of": "2026-11-09T20:00:00+00:00",
            "bikes_now": 10.0,
            "prediction_30min": 9.5,
            "prediction_60min": 9.0,
            "risk_level_30min": "faible",
        },
    )

    response = client.get("/stations/6245/prediction")

    assert response.status_code == 200
    body = response.json()
    assert body["station_id"] == 6245
    assert body["prediction_30min"] == 9.5
    assert body["prediction_60min"] == 9.0
    assert body["risk_level_30min"] == "faible"


def test_prediction_404_when_insufficient_recent_data(client, monkeypatch, tmp_path):
    (tmp_path / "lightgbm_30.joblib").write_text("fake")
    monkeypatch.setattr(predictions_module, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(predictions_module, "predict_station", lambda engine, station_id: None)

    response = client.get("/stations/999/prediction")

    assert response.status_code == 404


def test_prediction_503_when_model_not_trained(client, monkeypatch, tmp_path):
    # tmp_path vide : aucun lightgbm_30.joblib
    monkeypatch.setattr(predictions_module, "MODELS_DIR", tmp_path)

    response = client.get("/stations/6245/prediction")

    assert response.status_code == 503
