# Recife Rain Nowcasting

Machine learning for short-term heavy rainfall prediction in Recife, Brazil.

> Academic project developed at the Federal Rural University of Pernambuco (UFRPE).

[Read the technical article in PDF (27 pages)](docs/articles/artigo_recife_rain_nowcasting.pdf)
or see the [article documentation](docs/articles/README.md).

## Overview

Recife is frequently affected by intense rainfall, flooding, and other weather-related urban disruptions.

This project investigates whether historical meteorological observations can be used to identify patterns and predict heavy rainfall up to **six hours in advance** using Machine Learning.

The goal is not to replace official meteorological warning systems, but to explore a complementary data-driven approach capable of transforming meteorological data into information that can later be consumed by an accessible application.

## AlertaChuva Recife — citizen application

The purpose is **simple severe-rainfall notices for families in Recife**,
including people unfamiliar with technology. The home page shows the current
notice, forecast hours and one opt-in notification button, without accounts or
meteorological forms. The technical interface is retained at `/laboratorio`.
This is an installable web application (PWA).

The operator imports recent A301 observations from the official INMET table;
the six existing models then produce forecasts without retraining. Incomplete
or more-than-two-hour-old observations suppress forecasts and push alerts.
Historical demonstrations keep their original dates and cannot send weather push.

Web Push registration, encrypted delivery and a background monitor are
implemented. **Continuous automatic INMET ingestion, public HTTPS hosting and
end-to-end push verification on a real phone remain pending.** Citizens do not
enter measurements. See [application setup](app/README.md),
[product alignment](docs/PRODUCT_ALIGNMENT.md) and
[current validation](docs/validation/citizen_app_checks.json).

The PDF preserves the earlier software snapshot; these updated guides document
the current application. Scientific models/results are unchanged.

## Prediction Task

Given the meteorological information available at time `t`, the system will predict the occurrence of heavy rainfall independently for:

- +1 hour
- +2 hours
- +3 hours
- +4 hours
- +5 hours
- +6 hours

Each forecasting horizon will be evaluated separately.

## Dataset

The research uses hourly meteorological observations from an INMET weather station in Recife, Pernambuco, Brazil.

**Effective modeling period:** 2018-01-01 00:00 UTC through 2021-11-12 06:00 UTC,
using station **A301 (Recife)**. The original proposal covered 2018–2024;
2022–2023 meteorological variables were unavailable, and A301 data were not found
in the inspected official 2024 historical package.

Variables investigated include:

- precipitation
- temperature
- relative humidity
- atmospheric pressure
- wind measurements
- temporal features derived from the observation timestamp

Wind variables were investigated but excluded from the final supervised models
because of missingness. Missing measurements and targets are not replaced with
zero. The project-specific severe-rainfall definition is **precipitation >=
10.0 mm/h**; this is not an official INMET threshold.

## Methodology

The experimental data science workflow is complete:

1. Data collection and validation
2. Missing-data and temporal-continuity analysis
3. Exploratory Data Analysis (EDA)
4. Feature engineering
5. Creation of forecasting targets from +1h to +6h
6. Temporal train/validation/test split
7. Baseline model
8. Supervised Machine Learning
9. Model evaluation
10. Unsupervised clustering analysis
11. Prediction API
12. Application prototype

## Machine Learning

Supervised models compared:

- Dummy Classifier
- Logistic Regression
- Random Forest

Complementary unsupervised analysis:

- K-Means

Because heavy-rainfall events may be much less frequent than non-events, model evaluation will not rely on accuracy alone. Candidate metrics include:

- Precision
- Recall
- F1-score
- ROC-AUC
- PR-AUC
- Confusion Matrix

Final training uses 2018–2020; 2021 is reserved for evaluation. Selection uses
expanding folds (train 2018 / validate 2019, train 2018–2019 / validate 2020).
Every partition requires **observation time + horizon < partition end**, so
training and validation labels cannot enter a future reserved period.

## Validated Production Models — 2026-10-11

The user authorized a temporal label-boundary correction and repetition of
pre-2021 hyperparameter/threshold selection. This update supersedes the original
notebook results. Old results remain available as clearly identified history in
[the correction report](docs/validation/README.md).

| Horizon | Model | RF depth / leaf | Threshold |
|---|---|---|---:|
| +1h | Logistic Regression | — | 0.99 |
| +2h | Random Forest | None / 10 | 0.06 |
| +3h | Random Forest | 4 / 1 | 0.78 |
| +4h | Random Forest | 4 / 10 | 0.79 |
| +5h | Logistic Regression | — | 0.85 |
| +6h | Random Forest | 8 / 1 | 0.67 |

Logistic Regression uses StandardScaler in a training-only pipeline, `C=0.01`,
balanced class weights and `max_iter=3000`. Random Forest uses 300 estimators,
`balanced_subsample` weights and `n_jobs=-1`. Both use `random_state=42`.
The fixed, ordered 20-feature list lives in `src/features/schema.py`, shared by
training, inference and hourly-history feature construction.

The primary +1h model retains precision 0.170, recall 0.447 and F1 0.246 on the
2021 test: 17 true positives, 83 false positives and 21 false negatives.
Full corrected results and all historical comparisons are in the
[validation report](docs/validation/README.md) and its CSVs. Model choices use
validation Average Precision, with thresholds selected by pre-2021 OOF F1;
2021 results are not used to select or revise the configurations.

## Project Structure

```text
recife-rain-nowcasting-ml/
├── app/
├── data/
│   ├── raw/
│   ├── processed/
│   └── README.md
├── docs/
│   └── architecture.md
├── models/
├── notebooks/
├── src/
│   ├── data/
│   ├── evaluation/
│   ├── features/
│   └── models/
├── tests/
├── .gitignore
├── README.md
└── requirements.txt
```

## Current Status

A Portuguese technical article consolidates the methodology, corrected results,
software development and remaining current-data integration work:
[read the PDF](docs/articles/artigo_recife_rain_nowcasting.pdf).
Its [source template](docs/artigo_recife_rain_nowcasting.md) and
[document builder](docs/build_article.py) preserve reproducible tables without
changing the validated ML environment or rerunning training.

**Training, inference and reusable feature construction are implemented and
validated.** The six existing models are loaded once; inference returns scores
and alerts without fitting. A functional local web prototype supports manual
seven-hour history, historical examples, six horizon cards and JSON export.
See [the inference guide](docs/INFERENCE.md), [architecture](docs/architecture.md)
and [handoff](docs/PROJECT_HANDOFF.md).

### Roadmap

- [x] Add and document the INMET dataset
- [x] Audit dataset structure and quality
- [x] Check missing timestamps and duplicated observations
- [x] Perform exploratory data analysis
- [x] Define the operational heavy-rainfall threshold
- [x] Build forecasting targets for +1h to +6h
- [x] Establish baseline models
- [x] Train supervised ML models
- [x] Compare performance across forecasting horizons
- [x] Analyze meteorological patterns using clustering
- [x] Correct temporal label boundaries and revalidate model selection
- [x] Create reproducible training, serialized artifacts and metadata
- [x] Create a reusable prediction API and automated inference tests
- [x] Share feature definitions and causal history construction
- [x] Pin and check the validated runtime environment
- [x] Develop and test a local application prototype

Run the demonstration with the existing environment/artifacts:

```powershell
& .\.venv-repro\Scripts\python.exe -m app.server --port 8000
```

Then open [the local application](http://127.0.0.1:8000). See
[application instructions](app/README.md) and
[software validation evidence](docs/validation/productionization.md).
The citizen page uses imported recent A301 data. An automatic continuous station
feed remains pending; manual/historical input is available in the laboratory.

## Research Questions

The implementation is designed to support three main research directions:

1. Determine whether meteorological observations can support the classification/prediction of rainfall intensity.
2. Investigate recurring patterns among meteorological conditions associated with precipitation events.
3. Translate model outputs into information that can be presented clearly to non-technical users.

## Data Leakage Policy

All experiments must respect the forecasting timestamp.

Features used to predict an event at a future horizon may contain only information that would have been available at prediction time. Future measurements must never be used as model inputs.

Training, validation, and test sets will preserve temporal order instead of using a random split.

## Academic Context and Contributions

This repository contains the implementation associated with a collaborative academic research project at UFRPE.

As development progresses, this section should document:

- project contributors;
- each contributor's responsibilities;
- Luís Gabriel's specific technical contributions.

This distinction is important because the research is collaborative.

## Reproducibility

Use **Python 3.14.6**, matching `.python-version`. Environment setup:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
python -m src.check_environment
python -m pip check
```

For notebooks, install `requirements-dev.txt` and check with
`python -m src.check_environment --development`. See [environment details](docs/INFERENCE.md).

With existing artifacts, run tests without retraining:

```bash
python -m unittest discover -s tests -v
python -m src.models.predict features.tmp
```

`features.tmp` is a JSON object with 20 numeric features, or a list for a batch.
The [inference guide](docs/INFERENCE.md) provides a complete example and the
seven-hour history API. Integration tests explicitly skip if local files are absent.

Only when artifacts need generating, with the audited dataset available locally:

```bash
python -m src.models.train_final_models
```

This explicit training command uses the version-controlled
[validated configurations](docs/validation/validated_configurations.json) and
saves `models/model_1h.joblib` through `model_6h.joblib` plus
`model_metadata.json`. Each joblib contains the fitted estimator and the
metadata required to preserve features, horizon and alert threshold.
Processed datasets and generated model artifacts remain ignored by Git.

To reproduce the authorized selection correction and historical comparison:

```bash
python -m src.evaluation.revalidate_temporal_boundaries
```

See the [validation report](docs/validation/README.md) for the tested environment
versions, boundary counts and limitations of the recalculated historical test.

## Disclaimer

This repository is a research prototype.

It **must not be used as an official weather warning or emergency alert system**. For severe-weather warnings and emergency guidance, users should rely on official meteorological and civil-defense services.

## License

A project license has not yet been selected. Before adding a license, the research group should align on how the academic code and data may be reused.
