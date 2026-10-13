"""Inference contracts without training; integration reads existing artifacts only."""

import copy
import json
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

from src.models.predict import RainPredictor, validate_features
from src.models.train_final_models import FEATURE_COLUMNS, FINAL_CONFIGURATIONS, INPUT_PATH, OUTPUT_DIR
from src.models.config import PROJECT_ROOT, TRAINING_CUTOFF
from src.data.model_dataset import load_dataset


class FixedScores:
    def __init__(self, scores):
        self.scores = np.asarray(scores)

    def predict_proba(self, X):
        return np.column_stack([1 - self.scores, self.scores])


class FeatureValidationTests(unittest.TestCase):
    def setUp(self):
        self.features = {name: float(i) for i, name in enumerate(FEATURE_COLUMNS)}

    def test_reorders_without_modifying_input(self):
        frame = pd.DataFrame([self.features, self.features])[FEATURE_COLUMNS[::-1]]
        frame.index = ["same", "same"]
        original = frame.copy()
        result = validate_features(frame)
        self.assertEqual(list(result.columns), FEATURE_COLUMNS)
        self.assertEqual(result.index.tolist(), ["same", "same"])
        pd.testing.assert_frame_equal(frame, original)
        pd.testing.assert_frame_equal(validate_features(self.features), result.reset_index(drop=True).iloc[:1])

    def test_missing_extra_and_future_features_are_rejected(self):
        for invalid in (
            {k: v for k, v in self.features.items() if k != "humidity_pct"},
            {**self.features, "precipitation_future_1h": 20},
            {**self.features, "target_1h": 1},
            {**self.features, "wind_speed_ms": 0},
        ):
            with self.subTest(columns=list(invalid)), self.assertRaisesRegex(ValueError, "Invalid features"):
                validate_features(invalid)

    def test_nonfinite_nonreal_and_nonnumeric_values_are_rejected(self):
        for value in (np.nan, np.inf, -np.inf, None, True, "1.0", [1], 1 + 2j):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_features({**self.features, "humidity_pct": value})

    def test_empty_duplicate_and_wrong_containers_are_rejected(self):
        duplicate = pd.DataFrame([[1] * 21], columns=[*FEATURE_COLUMNS, FEATURE_COLUMNS[0]])
        for invalid in ([], 42, None, pd.DataFrame(columns=FEATURE_COLUMNS), duplicate):
            with self.subTest(container=type(invalid)), self.assertRaises(ValueError):
                validate_features(invalid)

    def test_threshold_equality_and_sample_positions(self):
        predictor = object.__new__(RainPredictor)
        predictor.thresholds = {h: c["threshold"] for h, c in FINAL_CONFIGURATIONS.items()}
        predictor.models = {
            h: FixedScores([t - 1e-8, t, t + 1e-8]) for h, t in predictor.thresholds.items()
        }
        frame = pd.DataFrame([self.features] * 3, index=[9, 9, 3])
        result = predictor.predict(frame)
        self.assertEqual(len(result), 18)
        self.assertEqual(result.horizon_hours.tolist(), list(range(1, 7)) * 3)
        self.assertEqual(result.alert.tolist(), [False] * 6 + [True] * 12)
        self.assertEqual(result.sample_position.tolist(), [0] * 6 + [1] * 6 + [2] * 6)

    def test_bad_estimator_probabilities_are_rejected(self):
        predictor = object.__new__(RainPredictor)
        predictor.thresholds = {h: c["threshold"] for h, c in FINAL_CONFIGURATIONS.items()}
        for scores in ([np.nan], [1.1], [-0.1]):
            predictor.models = {h: FixedScores(scores) for h in range(1, 7)}
            with self.subTest(scores=scores), self.assertRaisesRegex(ValueError, "invalid probabilities"):
                predictor.predict(self.features)


@unittest.skipUnless((OUTPUT_DIR / "model_metadata.json").exists() and INPUT_PATH.exists(),
                     "Generate local artifacts/dataset to run read-only integration tests.")
class ArtifactIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predictor = RainPredictor()
        cls.metadata = cls.predictor.metadata
        cls.bundles = {h: joblib.load(OUTPUT_DIR / f"model_{h}h.joblib") for h in range(1, 7)}

    def test_real_scores_equal_direct_artifact_predictions(self):
        X = pd.read_csv(INPUT_PATH).dropna(subset=FEATURE_COLUMNS)[FEATURE_COLUMNS].iloc[::5000]
        actual = self.predictor.predict(X)
        for horizon, bundle in self.bundles.items():
            rows = actual[actual.horizon_hours == horizon]
            direct = bundle["model"].predict_proba(X)[:, 1]
            np.testing.assert_allclose(rows.probability, direct, rtol=0, atol=1e-14)
            np.testing.assert_array_equal(rows.alert, direct >= bundle["decision_threshold"])

    def test_inference_reproduces_frozen_2021_metrics_without_fitting(self):
        df = load_dataset(INPUT_PATH)
        df = df.loc[(df.index >= TRAINING_CUTOFF) & df[FEATURE_COLUMNS].notna().all(axis=1)]
        result = self.predictor.predict(df[FEATURE_COLUMNS])
        expected = pd.read_csv(PROJECT_ROOT / "docs/validation/corrected_final_evaluation_results.csv").set_index("horizon_hours")
        for horizon in range(1, 7):
            eligible = df[f"eligible_final_{horizon}h"].to_numpy()
            rows = result.loc[result.horizon_hours == horizon].iloc[np.flatnonzero(eligible)]
            y = df.loc[eligible, f"target_{horizon}h"].astype(int)
            score, alert = rows.probability, rows.alert
            tn, fp, fn, tp = confusion_matrix(y, alert, labels=[0, 1]).ravel()
            record = expected.loc[horizon]
            self.assertEqual(len(y), record.test_samples)
            self.assertEqual(int(y.sum()), record.test_positives)
            np.testing.assert_array_equal([tp, fp, fn, tn], record[["true_positives", "false_positives", "false_negatives", "true_negatives"]].to_numpy(dtype=int))
            metrics = {
                "precision": precision_score(y, alert), "recall": recall_score(y, alert),
                "f1": f1_score(y, alert), "csi": tp / (tp + fp + fn),
                "average_precision": average_precision_score(y, score), "roc_auc": roc_auc_score(y, score),
            }
            for metric, value in metrics.items():
                with self.subTest(horizon=horizon, metric=metric):
                    self.assertAlmostEqual(value, record[metric], delta=1e-12)

    def test_cli_success_and_invalid_input_exit_code(self):
        features = pd.read_csv(INPUT_PATH).dropna(subset=FEATURE_COLUMNS)[FEATURE_COLUMNS].iloc[0].to_dict()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "features.json"
            for value, exit_code in ((features, 0), ({}, 2)):
                path.write_text(json.dumps(value), encoding="utf-8")
                completed = subprocess.run([
                    sys.executable, "-W", "ignore::UserWarning:sklearn.utils.parallel",
                    "-m", "src.models.predict", str(path),
                ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=60)
                self.assertEqual(completed.returncode, exit_code, completed.stderr)
                if exit_code == 0:
                    self.assertEqual(len(json.loads(completed.stdout)), 6)
                else:
                    self.assertIn("Inference error", completed.stderr)
            path.write_text('{"precipitation_mm": 0, "precipitation_mm": 10}', encoding="utf-8")
            completed = subprocess.run([
                sys.executable, "-m", "src.models.predict", str(path),
            ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=60)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("Duplicate JSON field", completed.stderr)

    def test_invalid_metadata_fails_before_unpickling(self):
        edits = [
            lambda m: m.update(station_code="OTHER"),
            lambda m: m.update(feature_columns=FEATURE_COLUMNS[::-1]),
            lambda m: m.update(artifact_format_version=2),
            lambda m: m["library_versions"].update({"scikit-learn": "0.0"}),
            lambda m: m.update(configuration_selection_sha256="wrong"),
            lambda m: m["models"].pop(),
            lambda m: m["models"][0].update(decision_threshold=0.5),
            lambda m: m["models"][0].update(artifact_file="../escape.joblib"),
            lambda m: m["models"][0].update(latest_training_target_utc="2021-01-01T00:00:00+00:00"),
            lambda m: m["models"][0].update(latest_training_target_utc="2020-12-31T23:00:00"),
            lambda m: m["models"][0].update(no_2021_training_targets="false"),
            lambda m: m.update(models=[None] * 6),
            lambda m: m.update(library_versions=[]),
        ]
        for edit in edits:
            metadata = copy.deepcopy(self.metadata)
            edit(metadata)
            with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
                (Path(directory) / "model_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
                with patch("src.models.predict.joblib.load") as loader, self.assertRaises(ValueError):
                    RainPredictor(directory)
                loader.assert_not_called()

    def test_artifact_metadata_and_estimator_changes_are_rejected(self):
        def mismatched_record(bundle):
            bundle["decision_threshold"] = 0.1

        def wrong_estimator(bundle):
            bundle["model"] = copy.deepcopy(bundle["model"])
            bundle["model"].named_steps["classifier"].set_params(C=1)

        def wrong_classes(bundle):
            bundle["model"] = copy.deepcopy(bundle["model"])
            bundle["model"].named_steps["classifier"].classes_ = np.array([1, 0])

        for mutate in (mismatched_record, wrong_estimator, wrong_classes):
            bundle = dict(self.bundles[1])
            mutate(bundle)
            with patch("src.models.predict.joblib.load", return_value=bundle), self.assertRaises(ValueError):
                RainPredictor()


if __name__ == "__main__":
    unittest.main()
