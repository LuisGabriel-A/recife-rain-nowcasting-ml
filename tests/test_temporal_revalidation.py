"""Regression checks for the corrected expanding temporal validation."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.evaluation import revalidate_temporal_boundaries as validation
from src.models import train_final_models as training


class TemporalValidationTests(unittest.TestCase):
    def dataset(self):
        times = pd.DatetimeIndex([], tz="UTC")
        for year in (2018, 2019, 2020):
            times = times.append(pd.date_range(f"{year}-01-01", periods=12, freq="h", tz="UTC"))
            times = times.append(pd.date_range(f"{year}-12-31 18:00", periods=6, freq="h", tz="UTC"))
        values = np.arange(len(times), dtype=float)
        df = pd.DataFrame({feature: values for feature in training.FEATURE_COLUMNS}, index=times)
        for horizon in range(1, 7):
            df[f"target_{horizon}h"] = values % 2
            df[f"eligible_final_{horizon}h"] = True
        return df

    def test_every_fold_purges_both_training_and_validation_labels(self):
        df = self.dataset()
        for _, train_end, val_end in validation.FOLDS:
            for horizon in range(1, 7):
                for start, end in ((training.DATA_START, train_end), (train_end, val_end)):
                    with self.subTest(horizon=horizon, start=start, end=end):
                        X, _ = training.select_period_data(df, horizon, start, end)
                        self.assertTrue((X.index >= start).all())
                        self.assertTrue((X.index + pd.Timedelta(hours=horizon) < end).all())

    def test_audit_reports_removed_samples_and_positive_labels(self):
        df = self.dataset()
        for horizon in range(1, 7):
            for year in (2019, 2020, 2021):
                end = pd.Timestamp(f"{year}-01-01", tz="UTC")
                boundary = (df.index < end) & (df.index + pd.Timedelta(hours=horizon) >= end)
                df.loc[boundary, f"target_{horizon}h"] = 1
        audit = validation.boundary_audit(df)
        self.assertEqual(len(audit), 30)
        for row in audit.itertuples():
            self.assertEqual(row.removed_samples, row.horizon_hours)
            self.assertEqual(row.removed_positives, row.horizon_hours)
            self.assertEqual(row.corrected_samples, row.original_samples - row.removed_samples)
            self.assertEqual(row.corrected_positives, row.original_positives - row.removed_positives)

    def test_selection_rejects_2021_before_any_candidate_is_fitted(self):
        df = self.dataset()
        df.index = df.index + pd.DateOffset(years=3)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            with self.assertRaisesRegex(ValueError, "pre-2021 observations only"):
                validation.select_configurations(df, Path(folder))
            self.assertFalse(list(Path(folder).iterdir()))

    def test_threshold_uses_original_grid_and_f1_tie_breaking(self):
        result = validation.choose_threshold(np.array([0, 0, 1, 1]), np.array([0.10, 0.20, 0.75, 0.95]))
        self.assertAlmostEqual(result["threshold"], 0.21)
        self.assertEqual(result["oof_f1"], 1.0)
        self.assertEqual(result["oof_recall"], 1.0)
        self.assertEqual(result["oof_precision"], 1.0)


if __name__ == "__main__":
    unittest.main()
