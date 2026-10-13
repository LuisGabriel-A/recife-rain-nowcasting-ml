"""Shared paths and frozen model factory; selection evidence remains the authority."""

import json
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.features.schema import FEATURE_COLUMNS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = PROJECT_ROOT / "data/processed/recife_2018_2021_model_dataset.csv"
OUTPUT_DIR = PROJECT_ROOT / "models"
DATA_START = pd.Timestamp("2018-01-01 00:00", tz="UTC")
DATA_END = pd.Timestamp("2021-11-12 06:00", tz="UTC")
TRAINING_CUTOFF = pd.Timestamp("2021-01-01 00:00", tz="UTC")
SEVERE_RAINFALL_THRESHOLD_MM_H = 10.0
RANDOM_STATE = 42
VALIDATED_CONFIGURATIONS_PATH = PROJECT_ROOT / "docs/validation/validated_configurations.json"
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
        class_weight="balanced_subsample", random_state=RANDOM_STATE, n_jobs=-1,
    )
