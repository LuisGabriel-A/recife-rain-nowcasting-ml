"""Causal features identical to notebook 03 and the validated model dataset."""

import numpy as np
import pandas as pd

from src.features.schema import FEATURE_COLUMNS, OBSERVATION_COLUMNS, validate_features, validate_numeric_frame


def build_current_features(observations):
    """Build one sample at the last timestamp from >=7 consecutive observed hours.

    Input: DataFrame or list of records, with datetime_utc (explicit timezone)
    and exactly the four OBSERVATION_COLUMNS. Returns a one-row UTC-indexed
    DataFrame. Every supplied observation must be finite; no gap is filled.
    """
    if isinstance(observations, list):
        observations = pd.DataFrame(observations)
    if not isinstance(observations, pd.DataFrame):
        raise ValueError("Observations must be a DataFrame or list of hourly records.")
    expected = {"datetime_utc", *OBSERVATION_COLUMNS}
    if not observations.columns.is_unique or set(observations.columns) != expected:
        raise ValueError("Observations require datetime_utc and exactly the four meteorological columns.")
    if len(observations) < 7:
        raise ValueError("At least seven consecutive hourly observations are required (t-6h through t).")
    times = []
    for value in observations["datetime_utc"]:
        time = pd.Timestamp(value)
        if pd.isna(time) or time.tzinfo is None:
            raise ValueError("Observation timestamps must include an explicit timezone, preferably UTC Z.")
        times.append(time.tz_convert("UTC"))
    index = pd.DatetimeIndex(times, name="datetime_utc")
    if (not index.is_unique or not index.is_monotonic_increasing
            or not index.floor("h").equals(index)
            or not (index[1:] - index[:-1] == pd.Timedelta(hours=1)).all()):
        raise ValueError("Observations must be unique, ordered, consecutive and aligned to whole UTC hours.")
    raw = observations[OBSERVATION_COLUMNS].copy()
    validate_numeric_frame(raw)
    # Input checks catch invalid measurements, without introducing a new scaler/filter.
    if ((raw.precipitation_mm < 0).any()
            or ((raw.humidity_pct < 0) | (raw.humidity_pct > 100)).any()
            or (raw.pressure_station_mb <= 0).any()):
        raise ValueError("Invalid physical values: rainfall >=0, humidity 0..100, pressure >0 required.")
    raw.index = index
    features = raw.copy()
    features["hour_sin"] = np.sin(2 * np.pi * index.hour / 24)
    features["hour_cos"] = np.cos(2 * np.pi * index.hour / 24)
    features["day_of_year_sin"] = np.sin(2 * np.pi * index.dayofyear / 365.25)
    features["day_of_year_cos"] = np.cos(2 * np.pi * index.dayofyear / 365.25)
    for lag in (1, 2, 3, 6):
        features[f"precipitation_lag_{lag}h"] = raw.precipitation_mm.shift(lag)
    for window in (3, 6):
        features[f"precipitation_sum_{window}h"] = raw.precipitation_mm.rolling(window, min_periods=window).sum()
    for column in OBSERVATION_COLUMNS[1:]:
        features[f"{column}_lag_1h"] = raw[column].shift(1)
        # Notebook change names omit the unit suffix.
        name = {"temperature_c": "temperature", "humidity_pct": "humidity", "pressure_station_mb": "pressure"}[column]
        features[f"{name}_change_1h"] = raw[column] - raw[column].shift(1)
    return validate_features(features[FEATURE_COLUMNS].iloc[[-1]])
