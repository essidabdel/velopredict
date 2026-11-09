from ingestion.backfill import RELIABILITY_THRESHOLD_MINUTES, is_reliable


def test_is_reliable_under_threshold():
    assert is_reliable(59.9) is True


def test_is_reliable_at_threshold():
    assert is_reliable(60.0) is True


def test_is_reliable_over_threshold():
    assert is_reliable(60.1) is False


def test_is_reliable_uses_default_threshold():
    assert is_reliable(RELIABILITY_THRESHOLD_MINUTES) is True
    assert is_reliable(RELIABILITY_THRESHOLD_MINUTES + 0.1) is False


def test_is_reliable_real_world_values_from_index():
    # Valeurs réelles observées dans daily/index.csv (tibzsecondaire/velib-data)
    assert is_reliable(31.6) is True  # 2026-10-25
    assert is_reliable(144.8) is False  # 2026-10-26
    assert is_reliable(54.8) is True  # 2026-11-01
    assert is_reliable(69.2) is False  # 2026-11-02
