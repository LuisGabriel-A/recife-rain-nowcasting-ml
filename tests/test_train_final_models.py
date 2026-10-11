"""Training boundary checks and a real six-model serialization round trip."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.models import train_final_models as training


TEST_DIR = Path(__file__).resolve().parent


def sample_dataset():
    times = pd.date_range("2018-01-01", periods=24, freq="h", tz="UTC")
    times = times.append(pd.date_range("2020-12-31 18:00", periods=13, freq="h", tz="UTC"))
    values = np.arange(len(times), dtype=float)
    df = pd.DataFrame({name: values + i for i, name in enumerate(training.FEATURE_COLUMNS)}, index=times)
    df.index.name = "datetime_utc"
    for horizon in range(1, 7):
        df[f"target_{horizon}h"] = values % 2
        df[f"eligible_final_{horizon}h"] = (times.year == 2018) | (times.year == 2021)
    df.loc[df.index[0], "eligible_final_2h"] = False
    return df


class TrainingTests(unittest.TestCase):
    def setUp(self):
        self.df = sample_dataset()

    def test_selection_respects_each_flag_and_ignores_test_values(self):
        for horizon in range(1, 7):
            with self.subTest(horizon=horizon):
                X, y = training.select_training_data(self.df, horizon)
                self.assertEqual(len(X), 23 if horizon == 2 else 24)
                self.assertTrue((X.index.year == 2018).all())
                self.assertEqual(list(X.columns), training.FEATURE_COLUMNS)
                changed = self.df.copy()
                changed.loc[changed.index.year == 2021, training.FEATURE_COLUMNS] = 1e12
                changed.loc[changed.index.year == 2021, f"target_{horizon}h"] = np.nan
                actual_X, actual_y = training.select_training_data(changed, horizon)
                pd.testing.assert_frame_equal(actual_X, X)
                pd.testing.assert_series_equal(actual_y, y)

    def test_labels_crossing_each_reserved_period_are_purged(self):
        for horizon in range(1, 7):
            for year in (2019, 2020, 2021):
                with self.subTest(horizon=horizon, year=year):
                    df = self.df.copy()
                    df.loc[df.index.year == 2020, f"eligible_final_{horizon}h"] = True
                    df.index = df.index - pd.DateOffset(years=2021 - year)
                    cutoff = pd.Timestamp(f"{year}-01-01", tz="UTC")
                    original = df.loc[(df.index < cutoff) & df[f"eligible_final_{horizon}h"]]
                    X, _ = training.select_period_data(df, horizon, df.index.min(), cutoff)
                    self.assertEqual(len(original) - len(X), horizon)
                    self.assertTrue((X.index + pd.Timedelta(hours=horizon) < cutoff).all())

    def test_missing_and_infinite_eligible_features_are_rejected(self):
        for value in (np.nan, np.inf, -np.inf):
            with self.subTest(value=value):
                df = self.df.copy()
                df.loc[df.index[0], "precipitation_mm"] = value
                with self.assertRaisesRegex(ValueError, "missing/infinite"):
                    training.select_training_data(df, 1)

    def test_missing_nonbinary_and_single_class_targets_are_rejected(self):
        for value in (np.nan, 0.5, 2):
            with self.subTest(value=value):
                df = self.df.copy()
                df.loc[df.index[0], "target_1h"] = value
                with self.assertRaisesRegex(ValueError, "observed binary"):
                    training.select_training_data(df, 1)
        df = self.df.copy()
        df["target_1h"] = 0
        with self.assertRaisesRegex(ValueError, "both target classes"):
            training.select_training_data(df, 1)

    def test_invalid_csv_schema_and_flags_are_rejected(self):
        cases = [
            (self.df.drop(columns="humidity_pct"), "Missing required columns"),
            (pd.concat([self.df, self.df.iloc[:1]]), "unique"),
            (self.df.assign(eligible_final_1h="False-ish"), "boolean flags"),
            (self.df.assign(eligible_final_1h=np.nan), "boolean flags"),
        ]
        outside_period = self.df.copy()
        outside_period.index = outside_period.index + pd.DateOffset(years=5)
        cases.append((outside_period, "effective period"))
        for df, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory(dir=TEST_DIR) as folder:
                path = Path(folder) / "dataset.csv"
                df.to_csv(path)
                with self.assertRaisesRegex(ValueError, message):
                    training.load_dataset(path)

    def test_all_horizons_are_validated_before_artifacts_are_written(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIR) as folder:
            input_path = Path(folder) / "dataset.csv"
            output_dir = Path(folder) / "models"
            df = self.df.copy()
            df.loc[df.index[0], "target_6h"] = np.nan
            df.to_csv(input_path)
            with self.assertRaisesRegex(ValueError, "observed binary"):
                training.train_final_models(input_path, output_dir)
            self.assertFalse(output_dir.exists())

    def test_real_training_scalers_and_serialized_artifacts(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIR) as folder:
            input_path = Path(folder) / "dataset.csv"
            output_dir = Path(folder) / "models"
            self.df.to_csv(input_path)
            with contextlib.redirect_stdout(io.StringIO()):
                metadata = training.train_final_models(input_path, output_dir)
            self.assertEqual(len(list(output_dir.glob("*.joblib"))), 6)
            restored_metadata = json.loads((output_dir / "model_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(restored_metadata, metadata)
            expected_thresholds = {1: 0.99, 2: 0.06, 3: 0.78, 4: 0.79, 5: 0.85, 6: 0.67}
            for record in metadata["models"]:
                horizon = record["horizon_hours"]
                artifact = joblib.load(output_dir / record["artifact_file"])
                model = artifact.pop("model")
                self.assertEqual(artifact, record)
                self.assertEqual(record["decision_threshold"], expected_thresholds[horizon])
                X, y = training.select_training_data(self.df, horizon)
                self.assertEqual(record["training_samples"], len(X))
                self.assertEqual(record["training_positives"], int(y.sum()))
                self.assertLess(pd.Timestamp(record["latest_training_target_utc"]), training.TRAINING_CUTOFF)
                self.assertEqual(list(model.feature_names_in_), training.FEATURE_COLUMNS)
                if isinstance(model, Pipeline):
                    scaler = model.named_steps["scaler"]
                    np.testing.assert_allclose(scaler.mean_, X.mean().to_numpy())
                    self.assertEqual(scaler.n_samples_seen_, len(X))
                probability = model.predict_proba(X.iloc[:3])[:, 1]
                self.assertTrue(np.isfinite(probability).all())
                self.assertTrue(((probability >= 0) & (probability <= 1)).all())


if __name__ == "__main__":
    unittest.main()
