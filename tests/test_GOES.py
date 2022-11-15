from goes2go import GOES


def test_GOES():
    """Create a GOES object"""
    G = GOES(satellite="noaa-goes16", domain="C")
    assert G.satellite == "noaa-goes16"
    assert G.domain == "C"


def test_GOES_latest():
    G = GOES()
    ds = G.latest()


def test_GOES_nearesttime():
    G = GOES()
    ds = G.nearesttime("2022-01-01")


def test_GOES_timerange():
    G = GOES()
    ds = G.timerange("2022-01-01 00:00", "2022-01-01 01:00")


def test_GOES_df():
    G = GOES()
    df = G.df("2022-01-01 00:00", "2022-01-01 01:00")
