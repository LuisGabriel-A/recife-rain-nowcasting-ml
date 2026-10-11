"""Repeat notebook 10 selection after purging labels at every temporal boundary.

Run: python -m src.evaluation.revalidate_temporal_boundaries
Selection finishes and is saved before the separate 2021 evaluation is run.
Original experimental results are never overwritten.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score,
)

from src.models import train_final_models as training


RESULTS_DIR = training.PROJECT_ROOT / "docs/validation"
FOLDS = [
    ("2018_to_2019", pd.Timestamp("2019-01-01", tz="UTC"), pd.Timestamp("2020-01-01", tz="UTC")),
    ("2018_2019_to_2020", pd.Timestamp("2020-01-01", tz="UTC"), training.TRAINING_CUTOFF),
]
PARAMETER_GRIDS = {
    "logistic_regression": [{"C": value} for value in (0.01, 0.1, 1.0, 10.0)],
    "random_forest": [
        {"max_depth": depth, "min_samples_leaf": leaf}
        for depth in (4, 8, None) for leaf in (1, 10)
    ],
}


def boundary_audit(df):
    rows = []
    periods = [
        (f"{name}_train", training.DATA_START, train_end)
        for name, train_end, _ in FOLDS
    ] + [
        (f"{name}_validation", train_end, val_end)
        for name, train_end, val_end in FOLDS
    ] + [("final_train_2018_2020", training.DATA_START, training.TRAINING_CUTOFF)]
    for name, start, end in periods:
        for horizon in range(1, 7):
            original = df.loc[
                (df.index >= start) & (df.index < end) & df[f"eligible_final_{horizon}h"]
            ]
            removed = original.loc[original.index + pd.Timedelta(hours=horizon) >= end]
            rows.append({
                "period": name, "start_utc": start.isoformat(), "end_exclusive_utc": end.isoformat(),
                "horizon_hours": horizon,
                "original_samples": len(original),
                "original_positives": int(original[f"target_{horizon}h"].sum()),
                "removed_samples": len(removed),
                "removed_positives": int(removed[f"target_{horizon}h"].sum()),
                "corrected_samples": len(original) - len(removed),
                "corrected_positives": int(original[f"target_{horizon}h"].sum() - removed[f"target_{horizon}h"].sum()),
            })
    return pd.DataFrame(rows)


def choose_threshold(y_true, scores):
    """Original 0.01..0.99 grid; maximize F1, then recall, then precision."""
    rows = []
    for threshold in np.arange(0.01, 1.00, 0.01):
        prediction = (scores >= threshold).astype(int)
        rows.append({
            "threshold": float(threshold),
            "oof_precision": precision_score(y_true, prediction, zero_division=0),
            "oof_recall": recall_score(y_true, prediction, zero_division=0),
            "oof_f1": f1_score(y_true, prediction, zero_division=0),
        })
    return pd.DataFrame(rows).sort_values(
        ["oof_f1", "oof_recall", "oof_precision"], ascending=False
    ).iloc[0].to_dict()


def select_configurations(df, results_dir):
    """Select families/parameters by mean fold AP; this function rejects 2021."""
    if (df.index >= training.TRAINING_CUTOFF).any():
        raise ValueError("Selection input must contain pre-2021 observations only.")
    candidates, selected_families, configurations = [], [], {}
    for horizon in range(1, 7):
        fold_data = [
            (
                training.select_period_data(df, horizon, training.DATA_START, train_end),
                training.select_period_data(df, horizon, train_end, val_end),
            ) for _, train_end, val_end in FOLDS
        ]
        family_results = []
        for model_name, grid in PARAMETER_GRIDS.items():
            fitted_candidates = []
            for parameters in grid:
                config = {"model_name": model_name, **parameters}
                fold_ap, oof_true, oof_scores = [], [], []
                for (X_train, y_train), (X_val, y_val) in fold_data:
                    model = training.build_model(horizon, config)
                    model.fit(X_train, y_train)
                    scores = model.predict_proba(X_val)[:, 1]
                    fold_ap.append(float(average_precision_score(y_val, scores)))
                    oof_true.extend(y_val.to_numpy())
                    oof_scores.extend(scores)
                record = {
                    "horizon_hours": horizon, "model_name": model_name,
                    "parameters": json.dumps(parameters, sort_keys=True),
                    "fold_2019_ap": fold_ap[0], "fold_2020_ap": fold_ap[1],
                    "validation_mean_ap": float(np.mean(fold_ap)),
                }
                candidates.append(record)
                fitted_candidates.append((record, np.array(oof_true), np.array(oof_scores)))
            # Python's stable max preserves the original grid order on an AP tie.
            best, oof_true, oof_scores = max(fitted_candidates, key=lambda item: item[0]["validation_mean_ap"])
            result = {**best, **choose_threshold(oof_true, oof_scores)}
            selected_families.append(result)
            family_results.append(result)
            print(f"+{horizon}h {model_name}: {result['parameters']}, "
                  f"mean AP={result['validation_mean_ap']:.6f}, threshold={result['threshold']:.2f}", flush=True)
        best = max(family_results, key=lambda row: row["validation_mean_ap"])
        configurations[str(horizon)] = {
            "model_name": best["model_name"],
            "threshold": round(best["threshold"], 2),
            **json.loads(best["parameters"]),
        }
        pd.DataFrame(candidates).to_csv(results_dir / "corrected_grid_results.csv", index=False)
        pd.DataFrame(selected_families).to_csv(results_dir / "corrected_validation_selection.csv", index=False)
    selection = {
        "temporal_boundary_policy": "observation_time + horizon < partition_end",
        "family_and_parameter_selection": "mean Average Precision across the two pre-2021 folds",
        "threshold_selection": "pre-2021 OOF F1, then recall, then precision; grid 0.01..0.99",
        "configurations": configurations,
    }
    (results_dir / "validated_configurations.json").write_text(
        json.dumps(selection, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return selection


def evaluate_selected(df, selection):
    """Evaluate the frozen selection on 2021 without making further choices."""
    rows = []
    for key, config in selection["configurations"].items():
        horizon = int(key)
        X_train, y_train = training.select_training_data(df, horizon)
        # The effective-period endpoint itself remains valid as an observed target.
        X_test, y_test = training.select_period_data(
            df, horizon, training.TRAINING_CUTOFF, training.DATA_END + pd.Timedelta(hours=1)
        )
        model = training.build_model(horizon, config)
        model.fit(X_train, y_train)
        scores = model.predict_proba(X_test)[:, 1]
        prediction = (scores >= config["threshold"]).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, prediction, labels=[0, 1]).ravel()
        rows.append({
            "horizon_hours": horizon, "model": config["model_name"],
            "threshold": config["threshold"],
            "train_samples": len(X_train), "train_positives": int(y_train.sum()),
            "test_samples": len(X_test), "test_positives": int(y_test.sum()),
            "test_prevalence_pct": float(y_test.mean() * 100),
            "precision": precision_score(y_test, prediction, zero_division=0),
            "recall": recall_score(y_test, prediction, zero_division=0),
            "f1": f1_score(y_test, prediction, zero_division=0),
            "csi": float(tp / (tp + fp + fn)) if tp + fp + fn else 0.0,
            "average_precision": average_precision_score(y_test, scores),
            "roc_auc": roc_auc_score(y_test, scores),
            "true_positives": int(tp), "false_positives": int(fp),
            "false_negatives": int(fn), "true_negatives": int(tn),
        })
    return pd.DataFrame(rows)


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df = training.load_dataset(training.INPUT_PATH)
    boundary_audit(df).to_csv(RESULTS_DIR / "temporal_boundary_audit.csv", index=False)
    selection = select_configurations(df.loc[df.index < training.TRAINING_CUTOFF], RESULTS_DIR)
    selection["dataset_sha256"] = hashlib.sha256(training.INPUT_PATH.read_bytes()).hexdigest()
    (RESULTS_DIR / "validated_configurations.json").write_text(
        json.dumps(selection, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    # Freeze all six choices before accessing any test feature or test label.
    corrected = evaluate_selected(df, selection)
    corrected.to_csv(RESULTS_DIR / "corrected_final_evaluation_results.csv", index=False)
    old = pd.read_csv(RESULTS_DIR / "history/final_evaluation_results.csv")
    old.merge(corrected, on="horizon_hours", suffixes=("_historical", "_corrected")).to_csv(
        RESULTS_DIR / "final_results_comparison.csv", index=False
    )
    print(corrected.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
