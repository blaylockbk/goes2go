## Brian Blaylock
## October 18, 2021

"""Some simple tests for the ABI data."""

from goes2go.data import goes_nearesttime, goes_latest


def test_nearesttime():
    ds = goes_nearesttime("2020-01-01", save_dir="$TMPDIR")


def test_latest():
    ds = goes_latest(save_dir="$TMPDIR")
