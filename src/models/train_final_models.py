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
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = PROJECT_ROOT / "data/processed/recife_2018_2021_model_dataset.csv"
OUTPUT_DIR = PROJECT_ROOT / "models"
DATA_START = pd.Timestamp("2018-01-01 00:00", tz="UTC")
DATA_END = pd.Timestamp("2021-11-12 06:00", tz="UTC")
TRAINING_CUTOFF = pd.Timestamp("2021-01-01 00:00", tz="UTC")
SEVERE_RAINFALL_THRESHOLD_MM_H = 10.0
RANDOM_STATE = 42
VALIDATED_CONFIGURATIONS_PATH = PROJECT_ROOT / "docs/validation/validated_configurations.json"

FEATURE_COLUMNS = [
    "precipitation_mm",
    "temperature_c",
    "humidity_pct",
    "pressure_station_mb",
    "hour_sin",
    "hour_cos",
    "day_of_year_sin",
    "day_of_year_cos",
    "precipitation_lag_1h",
    "precipitation_lag_2h",
    "precipitation_lag_3h",
    "precipitation_lag_6h",
    "precipitation_sum_3h",
    "precipitation_sum_6h",
    "temperature_c_lag_1h",
    "humidity_pct_lag_1h",
    "pressure_station_mb_lag_1h",
    "temperature_change_1h",
    "humidity_change_1h",
    "pressure_change_1h",
]

# The tracked selection record is the single source of final configurations.
VALIDATION_RECORD = json.loads(VALIDATED_CONFIGURATIONS_PATH.read_text(encoding="utf-8"))
FINAL_CONFIGURATIONS = {
    int(horizon): config for horizon, config in VALIDATION_RECORD["configurations"].items()
}
if set(FINAL_CONFIGURATIONS) != set(range(1, 7)):
    raise ValueError("Validated configurations must cover exactly horizons +1h through +6h.")


def build_model(horizon, configuration=None):
    """Build the documented estimator without searching for new parameters."""
    config = FINAL_CONFIGURATIONS[horizon] if configuration is None else configuration
    if config["model_name"] == "logistic_regression":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                C=config.get("C", 0.01), class_weight="balanced", max_iter=3000,
                random_state=RANDOM_STATE,
            )),
        ])
    if config["model_name"] != "random_forest":
        raise ValueError(f"Unknown model family: {config['model_name']}")
    return RandomForestClassifier(
        n_estimators=300, max_depth=config["max_depth"],
        min_samples_leaf=config["min_samples_leaf"],
        class_weight="balanced_subsample", random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def load_dataset(input_path):
    """Load the audited dataset, rejecting ambiguous time or eligibility flags."""
    df = pd.read_csv(input_path)
    required = ["datetime_utc", *FEATURE_COLUMNS]
    for horizon in FINAL_CONFIGURATIONS:
        required.extend([f"target_{horizon}h", f"eligible_final_{horizon}h"])
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True)
    df = df.set_index("datetime_utc").sort_index()
    if df.empty or df.index.hasnans or not df.index.is_unique:
        raise ValueError("Dataset timestamps must be nonempty, unique and nonmissing.")
    if df.index.min() < DATA_START or df.index.max() > DATA_END:
        raise ValueError("Dataset timestamps fall outside the documented effective period.")
    for horizon in FINAL_CONFIGURATIONS:
        flag = df[f"eligible_final_{horizon}h"]
        if not pd.api.types.is_bool_dtype(flag) or flag.isna().any():
            raise ValueError(f"eligible_final_{horizon}h must contain boolean flags only.")
    return df


def select_period_data(df, horizon, start, end):
    """Keep eligible samples whose observations and labels lie in [start, end)."""
    flag_column = f"eligible_final_{horizon}h"
    target_column = f"target_{horizon}h"
    target_times = df.index + pd.Timedelta(hours=horizon)
    train = df.loc[
        (df.index >= start) & (df.index < end)
        & (target_times < end) & df[flag_column]
    ].copy()
    if train.empty:
        raise ValueError(f"+{horizon}h has no eligible samples in the requested period.")
    target_times = train.index + pd.Timedelta(hours=horizon)
    if not ((train.index >= start) & (train.index < end) & (target_times < end)).all():
        raise ValueError(f"+{horizon}h observations/labels cross the requested temporal boundary.")
    X = train[FEATURE_COLUMNS]
    if not all(pd.api.types.is_numeric_dtype(dtype) for dtype in X.dtypes):
        raise ValueError(f"+{horizon}h training features must be numeric.")
    if X.isna().any().any() or not np.isfinite(X.to_numpy()).all():
        raise ValueError(f"+{horizon}h eligible training features contain missing/infinite values.")
    y = train[target_column]
    if y.isna().any() or not y.isin([0, 1]).all():
        raise ValueError(f"+{horizon}h eligible targets must be observed binary labels.")
    if y.nunique() != 2:
        raise ValueError(f"+{horizon}h training requires both target classes.")
    return X, y.astype(int)


def select_training_data(df, horizon):
    """Purge labels crossing the final cutoff as explicitly authorized by the user."""
    return select_period_data(df, horizon, DATA_START, TRAINING_CUTOFF)


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
