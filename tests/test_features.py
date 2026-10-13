"""Causal feature formulas, history validation and dataset parity."""

import unittest

import numpy as np
import pandas as pd

from src.features.build_features import build_current_features
from src.features.schema import FEATURE_COLUMNS, OBSERVATION_COLUMNS
from src.models.config import INPUT_PATH


def hourly_history():
    times = pd.date_range("2020-02-29 18:00", periods=7, freq="h", tz="UTC")
    return pd.DataFrame({
        "datetime_utc": times,
        "precipitation_mm": np.arange(7, dtype=float),
        "temperature_c": np.arange(20, 27, dtype=float),
        "humidity_pct": np.arange(70, 77, dtype=float),
        "pressure_station_mb": np.arange(1000, 1007, dtype=float),
    })


class FeatureEngineeringTests(unittest.TestCase):
    def test_exact_lags_sums_changes_and_leap_year_cycle(self):
        history = hourly_history()
        original = history.copy()
        X = build_current_features(history)
        self.assertEqual(list(X.columns), FEATURE_COLUMNS)
        self.assertEqual(X.index[0], history.datetime_utc.iloc[-1])
        row = X.iloc[0]
        self.assertEqual(row.precipitation_lag_6h, 0)
        self.assertEqual(row.precipitation_lag_1h, 5)
        self.assertEqual(row.precipitation_lag_2h, 4)
        self.assertEqual(row.precipitation_lag_3h, 3)
        self.assertEqual(row.precipitation_sum_3h, 15)
        self.assertEqual(row.precipitation_sum_6h, 21)
        self.assertEqual(row.temperature_c_lag_1h, 25)
        for name in ("temperature", "humidity", "pressure"):
            self.assertEqual(row[f"{name}_change_1h"], 1)
        self.assertAlmostEqual(row.hour_sin, 0)
        self.assertAlmostEqual(row.hour_cos, 1)
        self.assertAlmostEqual(row.day_of_year_sin, np.sin(2 * np.pi * 61 / 365.25))
        pd.testing.assert_frame_equal(history, original)

    def test_longer_history_and_timezone_offsets_have_identical_features(self):
        history = hourly_history()
        prefix = history.iloc[:1].copy()
        prefix.datetime_utc -= pd.Timedelta(hours=1)
        expected = build_current_features(history)
        pd.testing.assert_frame_equal(build_current_features(pd.concat([prefix, history])), expected)
        offset = history.copy()
        offset.datetime_utc = offset.datetime_utc.dt.tz_convert("America/Fortaleza")
        pd.testing.assert_frame_equal(build_current_features(offset.to_dict("records")), expected)

    def test_gaps_duplicates_unsorted_naive_and_subhourly_times_are_rejected(self):
        history = hourly_history()
        gap = history.copy()
        gap.loc[6, "datetime_utc"] += pd.Timedelta(hours=1)
        duplicate = history.copy()
        duplicate.loc[6, "datetime_utc"] = duplicate.loc[5, "datetime_utc"]
        naive = history.copy()
        naive.datetime_utc = naive.datetime_utc.dt.tz_localize(None)
        subhour = history.copy()
        subhour.datetime_utc += pd.Timedelta(minutes=30)
        for invalid in (gap, duplicate, naive, subhour, history.iloc[::-1], history.iloc[:6]):
            with self.subTest(times=invalid.datetime_utc.tolist()), self.assertRaises(ValueError):
                build_current_features(invalid)

    def test_invalid_measurements_and_label_columns_are_rejected(self):
        history = hourly_history()
        for value in (np.nan, np.inf, -1):
            invalid = history.copy()
            invalid.loc[0, "precipitation_mm"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_current_features(invalid)
        for invalid in (
            history.assign(humidity_pct=101), history.assign(pressure_station_mb=0),
            history.assign(temperature_c="20"), history.assign(target_1h=1),
            history.assign(precipitation_future_1h=20), history.drop(columns="humidity_pct"),
            history.assign(precipitation_mm=True),
        ):
            with self.subTest(columns=list(invalid)), self.assertRaises(ValueError):
                build_current_features(invalid)

    @unittest.skipUnless(INPUT_PATH.exists(), "Local dataset required for feature parity integration.")
    def test_features_match_validated_dataset_across_years(self):
        df = pd.read_csv(INPUT_PATH)
        df.datetime_utc = pd.to_datetime(df.datetime_utc, utc=True)
        valid = df[OBSERVATION_COLUMNS].notna().all(axis=1).rolling(7).sum().eq(7)
        indices = df.index[valid & df[FEATURE_COLUMNS].notna().all(axis=1)]
        selected = sorted(set(indices[::700].tolist() + [indices[-1]]))
        for index in selected:
            with self.subTest(timestamp=df.datetime_utc.iloc[index]):
                history = df.iloc[index - 6:index + 1][["datetime_utc", *OBSERVATION_COLUMNS]]
                actual = build_current_features(history).iloc[0].to_numpy(dtype=float)
                expected = df.loc[index, FEATURE_COLUMNS].to_numpy(dtype=float)
                np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-10)
        self.assertGreaterEqual(len(selected), 40)


if __name__ == "__main__":
    unittest.main()
