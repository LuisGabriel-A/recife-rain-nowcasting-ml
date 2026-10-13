"""Audited dataset loading and label-boundary-safe temporal selection."""

import numpy as np
import pandas as pd

from src.models.config import (DATA_START, DATA_END, TRAINING_CUTOFF, FEATURE_COLUMNS, FINAL_CONFIGURATIONS)


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
