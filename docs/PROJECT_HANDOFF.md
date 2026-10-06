# Project Handoff — Recife Rain Nowcasting ML

## 1. Project Status

Repository:

`recife-rain-nowcasting-ml`

The experimental Data Science stage is complete.

Completed stages:

- data acquisition and inspection;
- temporal data audit;
- preprocessing;
- feature engineering;
- multi-year consolidation;
- missing-data investigation;
- severe-rainfall target definition;
- temporal model-dataset preparation;
- baseline supervised models;
- decision-threshold optimization;
- temporal hyperparameter tuning;
- final supervised evaluation;
- unsupervised K-Means clustering;
- final figures and evaluation results.

Current stage:

`Productionization`

The next immediate task is to create reproducible production code for training and saving the final six forecasting models.

---

# 2. Research Goal

The project investigates short-term severe-rainfall nowcasting for Recife, Pernambuco, Brazil.

Hourly meteorological observations from the INMET automatic weather station A301 — Recife are used to predict whether severe rainfall will occur at future horizons from +1h through +6h.

The project also contains an unsupervised-learning component used to identify recurring meteorological regimes.

The final system is intended as a complementary machine-learning layer that may later support a mobile application.

It must not be presented as a replacement for official meteorological forecasting systems.

---

# 3. Original Scope vs Effective Scope

The original academic proposal considered observations from 2018 through 2024.

After auditing the available data, the effective modeling period became:

`2018-01-01 00:00 UTC`

through:

`2021-11-12 06:00 UTC`

The change was caused by source-data availability.

## 2022 and 2023

Rows for station A301 were present in the inspected source files, but the principal meteorological fields were effectively unavailable.

Raw availability for major variables was approximately:

- precipitation: 0%;
- pressure: 0%;
- temperature: 0%;
- humidity: 0%;
- wind direction: 0%;
- wind gust: 0%;
- wind speed: 0%.

Therefore 2022 and 2023 were excluded from modeling.

## 2024

A301 / Recife observations were not found in either:

- the inspected Kaggle 2024 file;
- the inspected official INMET 2024 historical ZIP package.

Do not claim that the station was necessarily inactive.

The correct wording is that A301 / Recife data were not found or were unavailable in the official historical package inspected.

Do not substitute another meteorological station without explicit approval.

---

# 4. 2021 Data Limitation

2021 contains valid A301 observations during most of the year but has a major continuous gap near the end of the available period.

Core meteorological completeness:

- first complete observation: 2021-01-01 00:00 UTC;
- last complete observation: 2021-11-12 06:00 UTC.

The major continuous missing period begins at:

`2021-11-12 07:00 UTC`

and continues through the end of the year.

Therefore the effective modeling period ends at:

`2021-11-12 06:00 UTC`

Missing observations within the retained period remain missing and must never automatically be replaced by zero.

---

# 5. Severe Rainfall Target

The operational severe-rainfall definition used by this project is:

`precipitation >= 10.0 mm/h`

This threshold was chosen as a project-specific, data-driven operational definition.

It is close to the 97.5th percentile of rainy-hour observations in the effective dataset.

It must not be described as an official INMET definition.

Before horizon-specific filtering, the effective period contained:

- total timestamps: 33,871;
- measured precipitation observations: 33,302;
- missing precipitation observations: 569;
- dry observations: 28,777;
- rainy observations: 4,525;
- severe observations at >= 10 mm/h: 109.

The positive class represents approximately:

`0.327%`

of valid precipitation observations.

This is therefore an extremely imbalanced classification problem.

---

# 6. Forecast Horizons

Six binary prediction targets were created:

- `target_1h`
- `target_2h`
- `target_3h`
- `target_4h`
- `target_5h`
- `target_6h`

At prediction timestamp `t`, each target represents whether precipitation at `t + horizon` is greater than or equal to 10 mm/h.

Missing future precipitation remains a missing target.

Missing future observations must never be converted to class 0.

---

# 7. Temporal Validation Strategy

Random temporal splitting is prohibited for the final methodology.

The final chronological split is:

## Final training period

`2018-01-01` through `2020-12-31`

## Final test period

`2021-01-01` through `2021-11-12`

2021 must remain unseen during model configuration decisions.

The 2021 data must not be used to:

- choose hyperparameters;
- select model families;
- choose classification thresholds;
- fit StandardScaler;
- fit the final production models.

---

# 8. Hyperparameter Validation

Temporal model tuning was performed with expanding windows.

Fold 1:

`train 2018 -> validate 2019`

Fold 2:

`train 2018–2019 -> validate 2020`

Model configurations were selected primarily using mean validation Average Precision.

Decision thresholds were selected using combined out-of-fold predictions from the pre-2021 validation periods.

After configuration and threshold selection, models were trained using all eligible data from 2018–2020 and evaluated once on 2021.

---

# 9. Final Supervised Feature Set

The final supervised dataset contains 20 features.

## Current meteorological state

- `precipitation_mm`
- `temperature_c`
- `humidity_pct`
- `pressure_station_mb`

## Temporal cyclical variables

- `hour_sin`
- `hour_cos`
- `day_of_year_sin`
- `day_of_year_cos`

## Precipitation history

- `precipitation_lag_1h`
- `precipitation_lag_2h`
- `precipitation_lag_3h`
- `precipitation_lag_6h`
- `precipitation_sum_3h`
- `precipitation_sum_6h`

## Meteorological history

- `temperature_c_lag_1h`
- `humidity_pct_lag_1h`
- `pressure_station_mb_lag_1h`

## Short-term atmospheric change

- `temperature_change_1h`
- `humidity_change_1h`
- `pressure_change_1h`

No future variable is allowed in the feature set.

---

# 10. Wind Feature Decision

Wind features were initially evaluated.

The following were removed from the final supervised feature set:

- `wind_gust_ms`
- `wind_speed_ms`
- `wind_speed_ms_lag_1h`
- `wind_direction_sin`
- `wind_direction_cos`

Reason:

approximately 46% of wind-related training observations were missing.

Using these features reduced complete training observations from approximately:

`97%`

to:

`63%`

and eliminated many rare severe-rainfall examples.

For example, wind-related features caused the loss of roughly 27–30 severe training observations depending on horizon.

The project chose feature removal instead of artificial imputation.

Do not silently reintroduce these variables.

---

# 11. Final Model Dataset

Final dataset:

`data/processed/recife_2018_2021_model_dataset.csv`

Dataset size:

`33,871 rows`

Final feature completeness:

`97.08%`

Complete-feature observations:

`32,881`

Incomplete-feature observations:

`990`

---

# 12. Final Eligible Training/Test Samples

Approximate final eligible samples by horizon:

## +1h

Training:

- samples: 25,586
- positive: 70

Test:

- samples: 7,248
- positive: 38

## +2h

Training:

- samples: 25,571
- positive: 70

Test:

- samples: 7,246
- positive: 38

## +3h

Training:

- samples: 25,555
- positive: 70

Test:

- samples: 7,244
- positive: 38

## +4h

Training:

- samples: 25,542
- positive: 70

Test:

- samples: 7,242
- positive: 38

## +5h

Training:

- samples: 25,530
- positive: 69

Test:

- samples: 7,239
- positive: 38

## +6h

Training:

- samples: 25,519
- positive: 69

Test:

- samples: 7,237
- positive: 38

---

# 13. Baseline Models

Initial supervised baselines included:

- DummyClassifier;
- Logistic Regression;
- Random Forest.

Because the positive class represents less than 1% of observations, accuracy is not considered an appropriate primary metric.

Main metrics:

- Precision;
- Recall;
- F1;
- Critical Success Index;
- Average Precision / PR-AUC;
- ROC-AUC;
- confusion matrix components.

The DummyClassifier predicted no positive cases.

---

# 14. Final Tuned Configurations

These model configurations were selected before observing the final 2021 test results.

Do not alter them silently.

## +1h

Model:

`LogisticRegression`

Parameters:

- `C = 0.01`
- `class_weight = "balanced"`
- `max_iter = 3000`
- `random_state = 42`

Preprocessing:

`StandardScaler` inside a sklearn Pipeline.

Decision threshold:

`0.99`

---

## +2h

Model:

`RandomForestClassifier`

Parameters:

- `n_estimators = 300`
- `max_depth = None`
- `min_samples_leaf = 10`
- `class_weight = "balanced_subsample"`
- `random_state = 42`
- `n_jobs = -1`

Decision threshold:

`0.13`

---

## +3h

Model:

`RandomForestClassifier`

Parameters:

- `n_estimators = 300`
- `max_depth = 4`
- `min_samples_leaf = 1`
- `class_weight = "balanced_subsample"`
- `random_state = 42`
- `n_jobs = -1`

Decision threshold:

`0.77`

---

## +4h

Model:

`LogisticRegression`

Parameters:

- `C = 0.01`
- `class_weight = "balanced"`
- `max_iter = 3000`
- `random_state = 42`

Preprocessing:

`StandardScaler` inside the Pipeline.

Decision threshold:

`0.94`

---

## +5h

Model:

`LogisticRegression`

Parameters:

- `C = 0.01`
- `class_weight = "balanced"`
- `max_iter = 3000`
- `random_state = 42`

Preprocessing:

`StandardScaler` inside the Pipeline.

Decision threshold:

`0.85`

---

## +6h

Model:

`RandomForestClassifier`

Parameters:

- `n_estimators = 300`
- `max_depth = 8`
- `min_samples_leaf = 10`
- `class_weight = "balanced_subsample"`
- `random_state = 42`
- `n_jobs = -1`

Decision threshold:

`0.57`

---

# 15. Final 2021 Supervised Results

## +1h — Logistic Regression

- Precision: 0.170
- Recall: 0.447
- F1: 0.246
- CSI: 0.140
- Average Precision: 0.225
- ROC-AUC: 0.945
- True positives: 17
- False positives: 83
- False negatives: 21

This is the primary model/result of the project.

---

## +2h — Random Forest

- Precision: 0.056
- Recall: 0.395
- F1: 0.098
- CSI: 0.051
- Average Precision: 0.076
- ROC-AUC: 0.866
- True positives: 15
- False positives: 254
- False negatives: 23

---

## +3h — Random Forest

- Precision: 0.090
- Recall: 0.526
- F1: 0.154
- CSI: 0.083
- Average Precision: 0.071
- ROC-AUC: 0.898
- True positives: 20
- False positives: 202
- False negatives: 18

---

## +4h — Logistic Regression

- Precision: 0.097
- Recall: 0.368
- F1: 0.153
- CSI: 0.083
- Average Precision: 0.075
- ROC-AUC: 0.897
- True positives: 14
- False positives: 131
- False negatives: 24

---

## +5h — Logistic Regression

- Precision: 0.038
- Recall: 0.526
- F1: 0.071
- CSI: 0.037
- Average Precision: 0.049
- ROC-AUC: 0.861
- True positives: 20
- False positives: 504
- False negatives: 18

---

## +6h — Random Forest

- Precision: 0.032
- Recall: 0.237
- F1: 0.056
- CSI: 0.029
- Average Precision: 0.022
- ROC-AUC: 0.821
- True positives: 9
- False positives: 272
- False negatives: 29

---

# 16. Primary +1h Result

The strongest overall result is the +1h Logistic Regression model.

Final result:

- threshold: 0.99
- precision: 17.0%
- recall: 44.7%
- F1: 24.6%
- CSI: 14.0%
- PR-AUC: 22.5%
- ROC-AUC: 94.5%

There were 38 severe-rainfall observations in the 2021 test data.

The model:

- correctly detected 17;
- missed 21;
- generated 83 false positives.

The class prevalence in the test data is approximately 0.52%.

Therefore a PR-AUC of 0.225 is substantially above the random/prevalence baseline.

---

# 17. +1h Baseline vs Final

Initial +1h Logistic Regression baseline:

- Precision: 0.016
- Recall: 0.947
- F1: 0.031
- Average Precision: 0.206
- ROC-AUC: 0.925

Final +1h Logistic Regression:

- Precision: 0.170
- Recall: 0.447
- F1: 0.246
- Average Precision: 0.225
- ROC-AUC: 0.945

The final model trades some recall for a very substantial reduction in false-positive alerts.

---

# 18. +1h Logistic Regression Interpretation

Largest standardized coefficients included:

- `humidity_pct`: +1.793
- `humidity_pct_lag_1h`: +1.735
- `temperature_c_lag_1h`: +1.005
- `temperature_c`: +0.823
- `day_of_year_sin`: +0.544
- `temperature_change_1h`: -0.506
- `precipitation_mm`: +0.489
- `day_of_year_cos`: -0.355
- `precipitation_lag_3h`: +0.346
- `humidity_change_1h`: +0.153

These values represent model associations.

Do not interpret them as causal meteorological relationships.

---

# 19. Unsupervised Learning

K-Means clustering was applied independently from the supervised target construction.

Variables used:

- precipitation;
- temperature;
- humidity;
- atmospheric pressure.

Precipitation was transformed using:

`np.log1p(precipitation_mm)`

Variables were standardized using StandardScaler.

Candidate cluster counts:

- K = 2
- K = 3
- K = 4
- K = 5
- K = 6

Final selection:

`K = 3`

Silhouette Score:

`0.3764`

---

# 20. Cluster Interpretation

Clusters were reordered from lowest to highest mean precipitation.

## Cluster 0 — warm_dry

Approximate characteristics:

- samples: 15,376
- share: 46.32%
- mean precipitation: 0.006 mm
- mean temperature: 28.38 C
- mean humidity: 66.44%
- rainy hours: 1.97%
- severe current rainfall hours: 0

---

## Cluster 1 — humid_low_rain

Approximate characteristics:

- samples: 16,207
- share: 48.83%
- mean precipitation: 0.066 mm
- mean temperature: 23.89 C
- mean humidity: 86.95%
- rainy hours: 15.84%
- severe current rainfall hours: 0

---

## Cluster 2 — rainy_high_humidity

Approximate characteristics:

- samples: 1,610
- share: 4.85%
- mean precipitation: 3.888 mm
- median precipitation: 2.4 mm
- maximum precipitation: 45.6 mm
- mean temperature: 23.77 C
- mean humidity: 91.56%
- rainy hours: 100%
- current severe rainfall hours: 109
- current severe rainfall percentage: 6.77%

All 109 current severe-rainfall observations were contained in Cluster 2.

This does not mean that clustering is itself a forecasting model.

---

# 21. Severe Rainfall in the Following Hour by Cluster

Observed +1h severe-rain frequency:

## Cluster 0

`0.046%`

## Cluster 1

`0.266%`

## Cluster 2

`3.669%`

Cluster 2 therefore represents a meteorological regime strongly associated with elevated short-term severe-rainfall risk.

This association must not be described as causal.

---

# 22. PCA Result

For visualization of the clustering solution:

- PC1 explained approximately 53.1%;
- PC2 explained approximately 23.3%;
- total explained variance: approximately 76.4%.

---

# 23. Completed Notebooks

The current notebook sequence is:

1. `notebooks/01_data_audit.ipynb`
2. `notebooks/02_data_preprocessing.ipynb`
3. `notebooks/03_feature_engineering.ipynb`
4. `notebooks/04_dataset_consolidation.ipynb`
5. `notebooks/05_final_dataset_audit.ipynb`
6. `notebooks/06_target_definition.ipynb`
7. `notebooks/07_model_dataset_preparation.ipynb`
8. `notebooks/08_baseline_models.ipynb`
9. `notebooks/09_threshold_optimization.ipynb`
10. `notebooks/10_model_tuning.ipynb`
11. `notebooks/11_clustering_analysis.ipynb`
12. `notebooks/12_final_evaluation.ipynb`

All twelve experimental notebooks are considered complete.

---

# 24. Important Processed Files

Important processed datasets/results include:

`data/processed/DataFrameRecife.csv`

Initial 2018 dataset.

---

`data/processed/recife_2018_preprocessed.csv`

2018 hourly preprocessing result.

---

`data/processed/recife_2018_features.csv`

Initial 2018 feature-engineering prototype.

---

`data/processed/recife_2018_2023_hourly.csv`

Multi-year consolidated audit dataset.

Despite the filename, 2022 and 2023 were later excluded from effective modeling because the meteorological variables were unavailable.

---

`data/processed/recife_2018_2021_targets.csv`

Final target dataset.

---

`data/processed/recife_2018_2021_model_dataset.csv`

Final 20-feature supervised model dataset.

This is the main input for production model training.

---

`data/processed/baseline_model_results.csv`

Baseline supervised results.

---

`data/processed/threshold_optimized_results.csv`

Threshold-optimization results.

---

`data/processed/tuned_model_results.csv`

Temporal hyperparameter-tuning results.

---

`data/processed/recife_2018_2021_clusters.csv`

Clustering assignments.

---

`data/processed/final_evaluation_results.csv`

Final supervised evaluation results.

---

# 25. Final Evaluation Figures

Generated figures are under:

`docs/figures/`

Important figures include:

- `final_classification_metrics.png`
- `final_ranking_metrics.png`
- `final_1h_confusion_matrix.png`
- `final_1h_precision_recall_curve.png`
- `final_1h_logistic_coefficients.png`

These figures are suitable for README and academic reporting.

---

# 26. Repository Structure

The intended repository structure is approximately:


recife-rain-nowcasting-ml/
├── AGENTS.md
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│   ├── README.md
│   ├── raw/
│   └── processed/
│
├── notebooks/
│
├── src/
│   ├── data/
│   ├── features/
│   ├── models/
│   └── evaluation/
│
├── models/
│
├── app/
│
├── tests/
│
└── docs/
    ├── PROJECT_HANDOFF.md
    ├── architecture.md
    └── figures/
---

## 27. Current Productionization Status

Productionization has NOT yet been completed.

At the time of this handoff:

- final experimental models have been defined;
- production training script has not yet been finalized;
- serialized `.joblib` models have not yet been generated as the official production artifacts;
- inference code has not yet been implemented;
- app integration has not yet been implemented.

The conversation paused specifically to create documentation before transferring work to Codex.

---

## 28. Immediate Next Task

The next task is:

`src/models/train_final_models.py`

The script must:

1. load `data/processed/recife_2018_2021_model_dataset.csv`;
2. use the established 20-feature list;
3. train one final model for every horizon from +1h to +6h;
4. use only observations earlier than 2021;
5. respect horizon-specific `eligible_final_Xh` flags;
6. reproduce the exact final configurations documented above;
7. preserve StandardScaler inside Logistic Regression pipelines;
8. save the six fitted artifacts;
9. save metadata describing the models;
10. explicitly validate that no 2021 observation enters model fitting.

---

## 29. Expected Model Artifacts

Expected generated artifacts:

- `models/model_1h.joblib`
- `models/model_2h.joblib`
- `models/model_3h.joblib`
- `models/model_4h.joblib`
- `models/model_5h.joblib`
- `models/model_6h.joblib`
- `models/model_metadata.json`

Each artifact should contain enough information for safe inference.

Recommended information:

- fitted sklearn model;
- forecast horizon;
- model name;
- decision threshold;
- ordered feature list;
- severe rainfall threshold;
- training cutoff.

---

## 30. Task After Model Serialization

After the final models are successfully created and validated, implement:

`src/models/predict.py`

The inference layer should:

1. load serialized model artifacts;
2. validate expected features;
3. preserve feature ordering;
4. generate probabilities for +1h through +6h;
5. apply the horizon-specific decision threshold;
6. return both probability/score and binary alert status;
7. reject malformed or incomplete input rather than silently changing values.

This inference layer will later be used by the application.

---

## 31. Later Remaining Tasks

After model training and inference:

1. reduce notebook-only duplicated logic by moving reusable code into `src/`;
2. add automated tests;
3. review `requirements.txt`;
4. finalize README;
5. update `docs/architecture.md`;
6. document limitations and reproduction commands;
7. connect inference code to the application/prototype;
8. prepare academic results/discussion text.

---

## 32. Git Practices

The user prefers explicit Git staging.

Use:

`git add <specific file>`

instead of:

`git add .`

Do not automatically commit or push without informing the user first.

Before committing:

1. inspect `git status`;
2. report modified/new files;
3. validate the relevant scripts;
4. stage specific files;
5. use a descriptive commit message.

---

## 33. Important Modeling Restrictions

Any coding agent continuing this repository must preserve the following.

Do not:

- use random train/test split for final evaluation;
- train final models using 2021;
- tune thresholds using 2021;
- fit scalers using 2021;
- convert missing precipitation to zero;
- introduce future variables into predictors;
- claim 2022–2024 data were successfully used;
- claim 10 mm/h is an official INMET severe-rain threshold;
- describe clustering associations as causal;
- silently replace station A301 with another station;
- silently reintroduce wind features;
- optimize directly against the final test metrics.

---

## 34. Reproducibility Principle

The final repository should allow a developer to reproduce the model artifacts from source code.

Notebooks document the experimental process.

Production scripts should reproduce the selected final models without manually executing notebook cells.

The codebase, not serialized binary files alone, must be the source of reproducibility.

---

## 35. Current Handoff Instruction for Codex

When Codex opens this repository, it should:

1. read `AGENTS.md`;
2. read this `docs/PROJECT_HANDOFF.md`;
3. inspect the current repository before changing files;
4. verify that the documented files actually exist;
5. preserve all documented methodological decisions;
6. continue from productionization;
7. implement `src/models/train_final_models.py`;
8. run and validate it;
9. report exactly which files were created or changed;
10. do not commit or push until explicitly authorized.

The next goal is not to redesign the Machine Learning experiment.

The next goal is to convert the completed experiment into a reproducible and usable software pipeline.


---

