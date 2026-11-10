from ml.predict import RISK_HIGH_THRESHOLD, RISK_MEDIUM_THRESHOLD, classify_risk_level


def test_classify_risk_level_eleve_at_or_below_high_threshold():
    assert classify_risk_level(0) == "eleve"
    assert classify_risk_level(RISK_HIGH_THRESHOLD) == "eleve"


def test_classify_risk_level_moyen_between_thresholds():
    assert classify_risk_level(RISK_HIGH_THRESHOLD + 0.1) == "moyen"
    assert classify_risk_level(RISK_MEDIUM_THRESHOLD) == "moyen"


def test_classify_risk_level_faible_above_medium_threshold():
    assert classify_risk_level(RISK_MEDIUM_THRESHOLD + 0.1) == "faible"
    assert classify_risk_level(50) == "faible"
