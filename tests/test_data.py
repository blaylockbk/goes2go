from datetime import datetime, timedelta
import unittest
from unittest.mock import patch
from venv import create

import pandas as pd

from goes2go.data import goes_nearesttime


def _test_row(
    satellite="G17",
    product="ABI-L1b-RadC",
    start=datetime(2021, 1, 1, 17, 0, 0),
    band=1,
    mode=6,
):
    return {
        "file": "fname",
        "product_mode": "pmode",
        "satellite": satellite,
        "start": start,
        "end": start + timedelta(seconds=60),
        "creation": start + timedelta(seconds=90),
        "product": product,
        "mode": mode,
        "band": band,
    }


class TestData(unittest.TestCase):
    def test_goes_nearesttime_singleband(self):
        t = datetime(2021, 1, 1, 17, 0, 0)

        with patch("goes2go.data._goes_file_df") as _goes_file_df_patched:
            test_df = pd.DataFrame([_test_row(start=t)])
            _goes_file_df_patched.return_value = test_df

            res = goes_nearesttime(
                t,
                satellite=17,
                product="ABI-L1b-Rad",
                return_as="filelist",
                bands=[1],
                download=False,
                domain="C",
            )
            self.assertEqual(len(res), 1)

    def test_goes_nearesttime_multiband(self):
        t = datetime(2021, 1, 1, 17, 0, 0)

        with patch("goes2go.data._goes_file_df") as _goes_file_df_patched:
            # test case where both have the same time, 2 res expected
            test_df = pd.DataFrame(
                [
                    _test_row(start=t, band=1),
                    _test_row(start=t, band=2),
                ]
            )
            _goes_file_df_patched.return_value = test_df
            res = goes_nearesttime(
                t,
                satellite=17,
                product="ABI-L1b-Rad",
                return_as="filelist",
                bands=[1, 2],
                download=False,
                domain="C",
            )
            self.assertEqual(len(res), 2)

            # test case where both have different time, 1 res expected
            test_df = pd.DataFrame(
                [
                    _test_row(start=t, band=1),
                    _test_row(start=t + timedelta(days=1), band=2),
                ]
            )
            _goes_file_df_patched.return_value = test_df
            res = goes_nearesttime(
                t,
                satellite=17,
                product="ABI-L1b-Rad",
                return_as="filelist",
                bands=[1, 2],
                download=False,
                domain="C",
            )
            self.assertEqual(len(res), 1)
            self.assertEqual(res.start[0], t)


if __name__ == "__main__":
    unittest.main()
