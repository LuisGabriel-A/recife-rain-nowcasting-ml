"""Read-only inference with the six temporally validated, trusted local artifacts."""

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.check_environment import check_environment
from src.data.json_input import parse_json
from src.features.schema import validate_features
from src.models.config import (
    FEATURE_COLUMNS, FINAL_CONFIGURATIONS, OUTPUT_DIR, TRAINING_CUTOFF,
    VALIDATED_CONFIGURATIONS_PATH, VALIDATION_RECORD, build_model,
)
class RainPredictor:
    """Load once and predict repeatedly. Joblib files must come from trusted training."""

    def __init__(self, model_dir=OUTPUT_DIR):
        check_environment()
        model_dir = Path(model_dir)
        self.metadata = parse_json((model_dir / "model_metadata.json").read_text(encoding="utf-8"))
        self._validate_metadata(self.metadata)
        records = self.metadata.get("models", [])
        if (not isinstance(records, list) or not all(isinstance(record, dict) for record in records)
                or len(records) != 6
                or {record.get("horizon_hours") for record in records} != set(range(1, 7))):
            raise ValueError("Model metadata must cover exactly horizons +1h through +6h.")
        self.models = {}
        self.thresholds = {}
        for record in records:
            self._validate_metadata(record)
            horizon = record["horizon_hours"]
            config = FINAL_CONFIGURATIONS[horizon]
            if (record.get("artifact_file") != f"model_{horizon}h.joblib"
                    or record.get("model_name") != config["model_name"]
                    or record.get("decision_threshold") != config["threshold"]):
                raise ValueError(f"+{horizon}h metadata differs from the validated configuration.")
            for key in ("training_end_utc", "latest_training_target_utc"):
                time = pd.Timestamp(record.get(key))
                if pd.isna(time) or time.tzinfo is None:
                    raise ValueError(f"+{horizon}h {key} needs a valid timezone-aware timestamp.")
                if time >= TRAINING_CUTOFF:
                    raise ValueError(f"+{horizon}h {key} reaches the reserved 2021 period.")
            if (record.get("no_2021_training_observations") is not True
                    or record.get("no_2021_training_targets") is not True):
                raise ValueError(f"+{horizon}h temporal audit is missing or failed.")
            # Validate readable metadata before unpickling anything.
            artifact = joblib.load(model_dir / record["artifact_file"])
            if not isinstance(artifact, dict) or {k: v for k, v in artifact.items() if k != "model"} != record:
                raise ValueError(f"+{horizon}h artifact and metadata disagree.")
            model = artifact["model"]
            expected = build_model(horizon)
            classifier = model.named_steps["classifier"] if isinstance(model, Pipeline) else model
            expected_classifier = expected.named_steps["classifier"] if isinstance(expected, Pipeline) else expected
            if (type(model) is not type(expected)
                    or type(classifier) is not type(expected_classifier)
                    or classifier.get_params() != expected_classifier.get_params()
                    or record.get("parameters") != classifier.get_params()
                    or record.get("preprocessing") != ("StandardScaler" if isinstance(expected, Pipeline) else None)):
                raise ValueError(f"+{horizon}h estimator differs from its validated configuration.")
            if isinstance(model, Pipeline):
                if (list(model.named_steps) != ["scaler", "classifier"]
                        or type(model.named_steps["scaler"]) is not type(expected.named_steps["scaler"])):
                    raise ValueError(f"+{horizon}h must preserve the fitted StandardScaler pipeline.")
            if (list(model.classes_) != [0, 1]
                    or model.n_features_in_ != len(FEATURE_COLUMNS)
                    or list(model.feature_names_in_) != FEATURE_COLUMNS):
                raise ValueError(f"+{horizon}h fitted classes/features are incompatible.")
            self.models[horizon] = model
            self.thresholds[horizon] = record["decision_threshold"]

    @staticmethod
    def _validate_metadata(metadata):
        if not isinstance(metadata, dict) or not isinstance(metadata.get("library_versions"), dict):
            raise ValueError("Model metadata and library_versions must be JSON objects.")
        required = {
            "artifact_format_version": 1, "station_code": "A301",
            "feature_columns": FEATURE_COLUMNS, "severe_rainfall_threshold_mm_h": 10.0,
            "training_cutoff_utc": TRAINING_CUTOFF.isoformat(),
            "training_cutoff_exclusive": True,
            "temporal_boundary_policy": "observation_time + horizon < partition_end",
            "dataset_sha256": VALIDATION_RECORD["dataset_sha256"],
            "configuration_selection_sha256": hashlib.sha256(VALIDATED_CONFIGURATIONS_PATH.read_bytes()).hexdigest(),
        }
        for key, expected in required.items():
            if metadata.get(key) != expected:
                raise ValueError(f"Incompatible model metadata: {key}.")
        for library in ("numpy", "pandas", "scikit-learn", "joblib"):
            if metadata.get("library_versions", {}).get(library) != version(library):
                raise ValueError(f"Use the recorded training version of {library} before loading artifacts.")

    def predict(self, features):
        """Return six scores/alerts per sample; probability is uncalibrated predict_proba."""
        X = validate_features(features)
        parts = []
        for horizon in range(1, 7):
            probabilities = self.models[horizon].predict_proba(X)
            if (probabilities.shape != (len(X), 2)
                    or not np.isfinite(probabilities).all()
                    or ((probabilities < 0) | (probabilities > 1)).any()):
                raise ValueError(f"+{horizon}h returned invalid probabilities.")
            score = probabilities[:, 1]
            parts.append(pd.DataFrame({
                "sample_position": np.arange(len(X)), "horizon_hours": horizon,
                "model_name": FINAL_CONFIGURATIONS[horizon]["model_name"],
                "probability": score, "decision_threshold": self.thresholds[horizon],
                "alert": score >= self.thresholds[horizon],
            }))
        return pd.concat(parts, ignore_index=True).sort_values(
            ["sample_position", "horizon_hours"], ignore_index=True,
        )


def main():
    parser = argparse.ArgumentParser(description="Predict +1h through +6h from exactly 20 numeric features.")
    parser.add_argument("input", type=Path, help="JSON object (one sample) or list of feature objects")
    parser.add_argument("--model-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    try:
        payload = parse_json(args.input.read_text(encoding="utf-8"))
        features = pd.DataFrame(payload) if isinstance(payload, list) else payload
        result = RainPredictor(args.model_dir).predict(features)
        print(result.to_json(orient="records", double_precision=15))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Inference error: {exc}\n")


if __name__ == "__main__":
    main()
