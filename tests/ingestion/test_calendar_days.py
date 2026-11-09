from datetime import date

from ingestion.calendar_days import local_date_range


def test_local_date_range_matches_toussaint_2017_example():
    # Vacances de la Toussaint 2017 : du 21/10 au 05/11 inclus (reprise le 06/11)
    days = local_date_range("2017-10-20T22:00:00+00:00", "2017-11-05T23:00:00+00:00")

    assert days[0] == date(2017, 10, 21)
    assert days[-1] == date(2017, 11, 5)
    assert len(days) == 16


def test_local_date_range_single_day_bridge():
    # Pont de l'Ascension : un seul jour
    days = local_date_range("2027-05-06T22:00:00+00:00", "2027-05-06T22:00:00+00:00")
    assert days == []
