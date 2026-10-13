"""Single ordered feature contract shared by training, inference and the app."""

from collections.abc import Mapping

import numpy as np
import pandas as pd


OBSERVATION_COLUMNS = ["precipitation_mm", "temperature_c", "humidity_pct", "pressure_station_mb"]
FEATURE_COLUMNS = [
    *OBSERVATION_COLUMNS,
    "hour_sin", "hour_cos", "day_of_year_sin", "day_of_year_cos",
    "precipitation_lag_1h", "precipitation_lag_2h", "precipitation_lag_3h", "precipitation_lag_6h",
    "precipitation_sum_3h", "precipitation_sum_6h",
    "temperature_c_lag_1h", "humidity_pct_lag_1h", "pressure_station_mb_lag_1h",
    "temperature_change_1h", "humidity_change_1h", "pressure_change_1h",
]


def validate_numeric_frame(frame):
    """Reject absent, nonfinite, complex, boolean or text observations without coercion."""
    for column, dtype in frame.dtypes.items():
        if (not pd.api.types.is_numeric_dtype(dtype)
                or pd.api.types.is_bool_dtype(dtype)
                or pd.api.types.is_complex_dtype(dtype)):
            raise ValueError(f"Feature {column} must contain real numbers, not text or booleans.")
    if frame.isna().any().any() or not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("Features must be complete and finite; missing values are not imputed.")


def validate_features(features):
    """Return an ordered copy; never impute, coerce text, or accept label columns."""
    if isinstance(features, Mapping):
        features = pd.DataFrame([features])
    if not isinstance(features, pd.DataFrame):
        raise ValueError("Features must be a mapping or a pandas DataFrame.")
    if features.empty or not features.columns.is_unique:
        raise ValueError("Features must contain rows and unique columns.")
    missing = sorted(set(FEATURE_COLUMNS) - set(features.columns))
    extra = sorted(set(features.columns) - set(FEATURE_COLUMNS), key=str)
    if missing or extra:
        raise ValueError(f"Invalid features: missing={missing}, extra={extra}.")
    ordered = features.loc[:, FEATURE_COLUMNS].copy()
    validate_numeric_frame(ordered)
    return ordered
