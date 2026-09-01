from dubio.engines.translation.duration import estimate_duration


def test_longer_text_longer_duration():
    assert estimate_duration("Ce faci?") < estimate_duration("Ce naiba faci acolo, băiete?")


def test_reasonable_range():
    d = estimate_duration("Ce faci, băiete?")
    assert 0.5 < d < 3.0
