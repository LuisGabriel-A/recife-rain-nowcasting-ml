# Architecture

The scientific pipeline and inference share feature definitions and frozen
configurations. Prediction is read-only: no fitting or threshold selection.

## Current pipeline

```text
INMET hourly observations
          |
          v
   Data validation
          |
          v
 Temporal preprocessing
          |
          +----------------------+
          |                      |
          v                      v
 Feature engineering       Clustering analysis
          |
          v
 Targets +1h ... +6h
          |
          v
 Temporal train/validation/test split
          |
          v
 Baseline + ML models
          |
          v
 Model evaluation
          |
          v
 Prediction interface/API
          |
          v
 Local application prototype
```

## Design principle

The project must keep the research pipeline reproducible and separate experimentation from reusable production code:

- `notebooks/`: investigation and documented experiments;
- `src/`: reusable preprocessing, features, training, prediction, and evaluation code;
- `data/`: source and generated datasets;
- `models/`: generated model artifacts;
- `app/`: local application/API integration;
- `tests/`: automated validation of reusable code.

## Reusable modules

| Location | Responsibility |
|---|---|
| docs/validation/ | Authorized correction, frozen configurations and historical/current results |
| src/data/model_dataset.py | Audited CSV validation and t+h < partition_end selection |
| src/data/json_input.py | Strict JSON parsing, rejecting duplicate fields and NaN constants |
| src/features/schema.py | Single ordered feature contract and strict numeric validation |
| src/features/build_features.py | Latest sample from observed hourly history, no imputation/future data |
| src/models/config.py | Shared paths/constants and deterministic model factory |
| src/models/train_final_models.py | Explicit offline fitting/serialization, never invoked by inference |
| src/models/predict.py | Load once, validate artifacts/environment, predict six scores/alerts |
| src/evaluation/revalidate_temporal_boundaries.py | Explicit reproduction of the approved correction |
| src/check_environment.py | Read-only check of pinned Python/runtime/dev versions |
| app/server.py | Localhost HTTP adapter, historical example loading, no fitting |
| app/static/ | Responsive Portuguese UI, editable seven-hour history and JSON export |

Online flow: hourly observations through t → causal feature builder → ordered
20-feature validation → six existing joblibs → fixed-threshold decisions → UI.
Prepared feature objects can also enter directly through schema validation.

## Scientific and runtime boundaries

Training uses eligible 2018–2020 observations with labels also before 2021.
Expanding-fold training and validation use the same strict label boundary.
LR scaling remains inside the fitted Pipeline. The 2021 holdout is never used
for model/threshold selection or production fitting. Clustering is separate
analysis and does not enter supervised inference.

Historical application examples may read 2021 observations to demonstrate frozen
inference; this never fits models or revises choices. No live ingestion or official
alerting service is implemented. Scores are uncalibrated; >=10 mm/h is the project's
operational definition. The prototype receives numerical JSON, not model uploads.
It requires trusted locally generated joblibs with the pinned environment;
metadata checks establish consistency, not binary-file authentication.

See [INFERENCE.md](INFERENCE.md) for contracts/commands and
[PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) for real implementation status.
