from goes2go import GOES


########################################################################


def test_GOES16():
    """Create a GOES object"""
    G = GOES(satellite="noaa-goes16", domain="C")
    assert G.satellite == "noaa-goes16"
    assert G.domain == "C"


def test_GOES16_latest():
    ds = GOES(satellite=16).latest()


def test_GOES16_nearesttime():
    ds = GOES(satellite=16).nearesttime("2022-01-01")


def test_GOES16_single_point_timerange():
    ds = GOES(satellite=16).single_point_timerange(38.897957, -77.036560, "2022-01-01 00:00", "2022-01-01 01:00")

def test_GOES16_timerange():
    ds = GOES(satellite=16).timerange("2022-01-01 00:00", "2022-01-01 01:00")

def test_GOES16_df():
    df = GOES(satellite=16).df("2022-01-01 00:00", "2022-01-01 01:00")


########################################################################


def test_GOES18():
    """Create a GOES object"""
    G = GOES(satellite="noaa-goes18", domain="C")
    assert G.satellite == "noaa-goes18"
    assert G.domain == "C"


def test_GOES18_latest():
    ds = GOES(satellite=18).latest()


def test_GOES18_nearesttime():
    ds = GOES(satellite=18).nearesttime("2023-07-01")


########################################################################


def test_GOES19():
    """Create a GOES object"""
    G = GOES(satellite="noaa-goes19", domain="C")
    assert G.satellite == "noaa-goes19"
    assert G.domain == "C"


def test_GOES19_latest():
    ds = GOES(satellite=19).latest()


def test_GOES19_nearesttime():
    ds = GOES(satellite=19).nearesttime("2025-01-01")


def test_GOES19_single_point_timerange():
    ds = GOES(satellite=19).single_point_timerange(38.897957, -77.036560, "2025-01-01 00:00", "2025-01-01 01:00")

def test_GOES19_timerange():
    ds = GOES(satellite=19).timerange("2025-01-01 00:00", "2025-01-01 01:00")

def test_GOES19_df():
    df = GOES(satellite=19).df("2025-01-01 00:00", "2025-01-01 01:00")
