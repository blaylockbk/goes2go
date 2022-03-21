## Brian Blaylock
## October 18, 2021

"""
Some simple tests for the GLM data
"""

from goes2go.data import goes_latest, goes_nearesttime, goes_timerange


def test_nearesttime():
    ds = goes_nearesttime("2020-01-01", product="glm", save_dir="$TMPDIR")


def test_latest():
    ds = goes_latest(product="glm", save_dir="$TMPDIR")
