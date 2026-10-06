# AGENTS.md

## Project

Repository: `recife-rain-nowcasting-ml`

This repository contains an academic Data Science / Machine Learning project focused on short-term severe-rainfall forecasting for Recife, Pernambuco, Brazil.

The project uses hourly meteorological observations from the INMET automatic weather station A301 (Recife).

The main supervised-learning task is binary classification of severe rainfall for forecast horizons from +1h to +6h.

The repository also includes an unsupervised-learning stage for identifying meteorological regimes through clustering.


## Critical Methodological Rules

These rules must not be changed without explicit user approval.

### Severe rainfall definition

The operational severe-rainfall threshold is:

`precipitation >= 10.0 mm/h`

This is a project-specific, data-driven operational definition.

Do not describe it as an official INMET severe-rainfall threshold.


### Forecast horizons

The project predicts severe rainfall at:

- +1 hour
- +2 hours
- +3 hours
- +4 hours
- +5 hours
- +6 hours


### Effective modeling period

The effective dataset period is:

`2018-01-01 00:00 UTC` through `2021-11-12 06:00 UTC`


### Data availability limitations

The original academic scope mentioned 2018–2024.

However:

- 2022 and 2023 contain station timestamps but the primary meteorological variables for A301 are unavailable in the inspected source data.
- A301 / Recife data were not found in the official 2024 historical package that was inspected.
- These years must not be silently introduced into the model.
- Do not substitute another station without explicit approval.


### Missing data

Missing meteorological observations must never automatically be interpreted as zero.

Do not silently impute missing observations.

Any imputation introduced in the future must be explicitly justified and fitted using training data only.


## Temporal Validation Strategy

Time order must always be respected.

Random train/test splitting is prohibited for final model evaluation.

The main final split is:

- Training: 2018–2020
- Final test: 2021

The 2021 observations must not be used to:

- choose hyperparameters;
- choose decision thresholds;
- select model architecture;
- fit feature scalers;
- fit final training models.

2021 is the unseen final test period.


## Hyperparameter Tuning Strategy

Hyperparameter selection was performed using expanding temporal validation before 2021:

1. train on 2018, validate on 2019;
2. train on 2018–2019, validate on 2020.

Average Precision (PR-AUC) was used for model configuration selection.

Decision thresholds were selected using out-of-fold predictions from the pre-2021 validation periods.


## Class Imbalance

Severe rainfall is extremely rare.

The positive class represents substantially less than 1% of observations.

Therefore:

- accuracy must not be used as the primary model-quality metric;
- precision, recall, F1, CSI and Average Precision are important;
- ROC-AUC may be reported but must not be interpreted alone;
- false positives and false negatives must be explicitly considered.


## Final Supervised Features

The final supervised feature set contains 20 predictors:

1. `precipitation_mm`
2. `temperature_c`
3. `humidity_pct`
4. `pressure_station_mb`
5. `hour_sin`
6. `hour_cos`
7. `day_of_year_sin`
8. `day_of_year_cos`
9. `precipitation_lag_1h`
10. `precipitation_lag_2h`
11. `precipitation_lag_3h`
12. `precipitation_lag_6h`
13. `precipitation_sum_3h`
14. `precipitation_sum_6h`
15. `temperature_c_lag_1h`
16. `humidity_pct_lag_1h`
17. `pressure_station_mb_lag_1h`
18. `temperature_change_1h`
19. `humidity_change_1h`
20. `pressure_change_1h`


## Wind Variables

Wind variables were evaluated but removed from the final supervised feature set.

The reason is data availability.

Approximately 46% of the training-period wind observations were unavailable, and requiring these features caused a substantial loss of rare severe-rainfall samples.

Do not reintroduce wind variables into the final supervised models without explicitly re-evaluating this problem.


## Final Model Configurations

These configurations were selected using pre-2021 validation.

Do not change them silently.


### +1h

Model:

`LogisticRegression`

Configuration:

- `C = 0.01`
- `class_weight = "balanced"`
- decision threshold = `0.99`

Final 2021 performance:

- Precision: `0.170`
- Recall: `0.447`
- F1: `0.246`
- CSI: `0.140`
- Average Precision: `0.225`
- ROC-AUC: `0.945`
- True positives: `17`
- False positives: `83`
- False negatives: `21`


### +2h

Model:

`RandomForestClassifier`

Configuration:

- `n_estimators = 300`
- `max_depth = None`
- `min_samples_leaf = 10`
- `class_weight = "balanced_subsample"`
- decision threshold = `0.13`


### +3h

Model:

`RandomForestClassifier`

Configuration:

- `n_estimators = 300`
- `max_depth = 4`
- `min_samples_leaf = 1`
- `class_weight = "balanced_subsample"`
- decision threshold = `0.77`


### +4h

Model:

`LogisticRegression`

Configuration:

- `C = 0.01`
- `class_weight = "balanced"`
- decision threshold = `0.94`


### +5h

Model:

`LogisticRegression`

Configuration:

- `C = 0.01`
- `class_weight = "balanced"`
- decision threshold = `0.85`


### +6h

Model:

`RandomForestClassifier`

Configuration:

- `n_estimators = 300`
- `max_depth = 8`
- `min_samples_leaf = 10`
- `class_weight = "balanced_subsample"`
- decision threshold = `0.57`


## Logistic Regression Scaling

Logistic Regression must use:

`StandardScaler`

inside a scikit-learn `Pipeline`.

The scaler must be fitted only using training observations.

Never fit a scaler using the entire dataset before temporal splitting.


## Primary Result

The primary final forecasting result is the +1h Logistic Regression model.

It currently provides the strongest overall supervised result and the strongest probability-ranking performance.

Do not claim that the model is equivalent to an official meteorological forecasting system.

The project is a complementary machine-learning approach based on observations from a single surface meteorological station.


## Unsupervised Learning

K-Means clustering was used for meteorological-regime analysis.

Clustering variables:

- precipitation;
- temperature;
- relative humidity;
- atmospheric pressure.

Wind variables were excluded because of missingness.

The severe-rainfall target was not used during cluster formation.


### Final clustering result

Selected number of clusters:

`K = 3`

Silhouette Score:

`0.3764`

Interpretation:

- Cluster 0: `warm_dry`
- Cluster 1: `humid_low_rain`
- Cluster 2: `rainy_high_humidity`

Cluster 2 represented approximately 4.85% of analyzed observations but contained all 109 current severe-rainfall hours.

Severe rainfall during the following hour occurred approximately:

- Cluster 0: `0.046%`
- Cluster 1: `0.266%`
- Cluster 2: `3.669%`

Clusters must not be described as causal relationships or independent forecasting models.


## Important Project Files

Final model-ready dataset:

`data/processed/recife_2018_2021_model_dataset.csv`

Final target dataset:

`data/processed/recife_2018_2021_targets.csv`

Final evaluation results:

`data/processed/final_evaluation_results.csv`

Tuned-model results:

`data/processed/tuned_model_results.csv`

Clustering dataset:

`data/processed/recife_2018_2021_clusters.csv`


## Notebook Progress

Completed notebooks:

- `01_data_audit.ipynb`
- `02_data_preprocessing.ipynb`
- `03_feature_engineering.ipynb`
- `04_dataset_consolidation.ipynb`
- `05_final_dataset_audit.ipynb`
- `06_target_definition.ipynb`
- `07_model_dataset_preparation.ipynb`
- `08_baseline_models.ipynb`
- `09_threshold_optimization.ipynb`
- `10_model_tuning.ipynb`
- `11_clustering_analysis.ipynb`
- `12_final_evaluation.ipynb`


## Current Project Stage

The experimental Data Science stage is complete.

The next stage is productionization.

Immediate priorities:

1. create reproducible final-model training code;
2. save trained model artifacts;
3. create model metadata;
4. implement inference code;
5. organize reusable code under `src/`;
6. improve tests;
7. finalize README and project documentation;
8. prepare application integration.


## Expected Model Artifacts

The project will generate:

- `models/model_1h.joblib`
- `models/model_2h.joblib`
- `models/model_3h.joblib`
- `models/model_4h.joblib`
- `models/model_5h.joblib`
- `models/model_6h.joblib`
- `models/model_metadata.json`

Generated binary model artifacts may remain ignored by Git if required by `.gitignore`.

The reproducible source code used to generate them must be version-controlled.


## Code Organization

Reusable production code belongs under:

- `src/data/`
- `src/features/`
- `src/models/`
- `src/evaluation/`

Notebooks should document experiments and analysis.

Avoid placing important reusable application logic only inside notebooks.


## Coding Guidelines

Prefer:

- Python;
- pandas;
- NumPy;
- scikit-learn;
- joblib;
- pathlib.

Use deterministic `random_state=42` when applicable.

Functions should have clear responsibilities.

Avoid duplicating feature definitions across many files when a shared implementation can be created safely.

Do not introduce new dependencies unless they provide a clear project benefit.


## Data Leakage Rules

Never create features using future observations relative to prediction time.

At prediction time `t`, features may use:

- observations at `t`;
- observations before `t`.

They must not use:

- precipitation at `t+1`;
- precipitation at `t+2`;
- or any other future meteorological observation.

Future precipitation columns exist only to construct labels and must never be model features.


## Git Rules

Do not commit or push automatically unless explicitly requested by the user.

Before committing:

1. inspect `git status`;
2. add specific files rather than using `git add .`;
3. summarize what changed;
4. allow the user to review significant changes.

Use descriptive commit messages.


## Documentation Rules

Keep methodology consistent across:

- code;
- notebooks;
- README;
- academic text;
- application documentation.

Do not claim data exist for years or periods that were excluded during the audit.

Always distinguish:

- observed data availability;
- project operational definitions;
- modeling choices;
- official meteorological definitions.


## Instructions for Coding Agents

Before modifying this repository:

1. read this `AGENTS.md`;
2. read `docs/PROJECT_HANDOFF.md` if it exists;
3. inspect the relevant existing files;
4. preserve established methodological decisions;
5. do not silently redesign the ML methodology;
6. ask before changing core modeling assumptions;
7. validate code after editing;
8. report files created or modified;
9. report commands executed;
10. report validation results and remaining issues.

When continuing the project, prioritize reproducibility and prevention of temporal data leakage over maximizing headline metrics.