"""Reproduce the six fixed A301 forecasting models; never tune on 2021.

Run from any directory with: python /path/to/src/models/train_final_models.py
Each joblib contains the fitted estimator and its inference metadata.
"""

import hashlib
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

# Keep the documented direct-script entry point usable from any directory.
if __package__ in (None, ''):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.models.config import (
    PROJECT_ROOT, INPUT_PATH, OUTPUT_DIR, DATA_START, DATA_END, TRAINING_CUTOFF,
    SEVERE_RAINFALL_THRESHOLD_MM_H, RANDOM_STATE, VALIDATED_CONFIGURATIONS_PATH,
    FEATURE_COLUMNS, VALIDATION_RECORD, FINAL_CONFIGURATIONS, build_model,
)


from src.data.model_dataset import load_dataset, select_period_data, select_training_data


def train_final_models(input_path=INPUT_PATH, output_dir=OUTPUT_DIR):
    """Fit and serialize all six models using validated training data only."""
    input_path, output_dir = Path(input_path), Path(output_dir)
    dataset_sha256 = hashlib.sha256(input_path.read_bytes()).hexdigest()
    if input_path.resolve() == INPUT_PATH.resolve() and dataset_sha256 != VALIDATION_RECORD["dataset_sha256"]:
        raise ValueError("The production dataset differs from the temporally validated selection dataset.")
    df = load_dataset(input_path)
    # Validate every horizon before fitting or writing any artifact.
    training_data = {
        horizon: select_training_data(df, horizon)
        for horizon in FINAL_CONFIGURATIONS
    }
    versions = {
        "python": platform.python_version(),
        **{name: version(name) for name in ("numpy", "pandas", "scikit-learn", "joblib")},
    }
    common = {
        "artifact_format_version": 1,
        "station_code": "A301",
        "feature_columns": FEATURE_COLUMNS,
        "severe_rainfall_threshold_mm_h": SEVERE_RAINFALL_THRESHOLD_MM_H,
        "severe_rainfall_definition": "Project operational threshold; not an official INMET definition.",
        "training_cutoff_utc": TRAINING_CUTOFF.isoformat(),
        "training_cutoff_exclusive": True,
        "temporal_boundary_policy": "observation_time + horizon < partition_end",
        "library_versions": versions,
        "dataset_sha256": dataset_sha256,
        "configuration_selection_file": str(VALIDATED_CONFIGURATIONS_PATH.relative_to(PROJECT_ROOT).as_posix()),
        "configuration_selection_sha256": hashlib.sha256(VALIDATED_CONFIGURATIONS_PATH.read_bytes()).hexdigest(),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    artifacts, records = {}, []
    for horizon, config in FINAL_CONFIGURATIONS.items():
        X, y = training_data[horizon]
        model = build_model(horizon)
        model.fit(X, y)
        classifier = model.named_steps["classifier"] if isinstance(model, Pipeline) else model
        record = {
            **common,
            "horizon_hours": horizon,
            "model_name": config["model_name"],
            "decision_threshold": config["threshold"],
            "parameters": classifier.get_params(),
            "preprocessing": "StandardScaler" if isinstance(model, Pipeline) else None,
            "artifact_file": f"model_{horizon}h.joblib",
            "training_samples": len(X),
            "training_positives": int(y.sum()),
            "boundary_samples_removed": int((
                (df.index < TRAINING_CUTOFF)
                & (df.index + pd.Timedelta(hours=horizon) >= TRAINING_CUTOFF)
                & df[f"eligible_final_{horizon}h"]
            ).sum()),
            "training_start_utc": X.index.min().isoformat(),
            "training_end_utc": X.index.max().isoformat(),
            "latest_training_target_utc": (X.index.max() + pd.Timedelta(hours=horizon)).isoformat(),
            "no_2021_training_observations": bool((X.index < TRAINING_CUTOFF).all()),
            "no_2021_training_targets": bool((X.index + pd.Timedelta(hours=horizon) < TRAINING_CUTOFF).all()),
        }
        artifacts[horizon] = {**record, "model": model}
        records.append(record)
        print(f"+{horizon}h: {len(X)} training samples, {int(y.sum())} positives; "
              f"{config['model_name']}, threshold={config['threshold']}", flush=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    for horizon, artifact in artifacts.items():
        artifact_path = output_dir / artifact["artifact_file"]
        joblib.dump(artifact, artifact_path)
        restored = joblib.load(artifact_path)
        X, _ = training_data[horizon]
        np.testing.assert_allclose(
            restored["model"].predict_proba(X.iloc[:5]),
            artifact["model"].predict_proba(X.iloc[:5]),
            rtol=0, atol=1e-14,
        )
    metadata = {
        **common,
        "dataset_file": input_path.name,
        "effective_period_start_utc": DATA_START.isoformat(),
        "effective_period_end_utc": DATA_END.isoformat(),
        "models": records,
    }
    metadata_path = output_dir / "model_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Saved and reloaded six model artifacts; metadata: {metadata_path}", flush=True)
    return metadata


if __name__ == "__main__":
    train_final_models()
