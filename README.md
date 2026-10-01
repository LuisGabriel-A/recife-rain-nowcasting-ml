# Recife Rain Nowcasting

Machine learning for short-term heavy rainfall prediction in Recife, Brazil.

> Academic project developed at the Federal Rural University of Pernambuco (UFRPE).

## Overview

Recife is frequently affected by intense rainfall, flooding, and other weather-related urban disruptions.

This project investigates whether historical meteorological observations can be used to identify patterns and predict heavy rainfall up to **six hours in advance** using Machine Learning.

The goal is not to replace official meteorological warning systems, but to explore a complementary data-driven approach capable of transforming meteorological data into information that can later be consumed by an accessible application.

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

**Research period:** 2018–2024.

Variables investigated include:

- precipitation
- temperature
- relative humidity
- atmospheric pressure
- wind measurements
- temporal features derived from the observation timestamp

> The exact station identifier, download URL, raw filenames, and data access date will be documented in `data/README.md` when the dataset is added to the repository.

## Methodology

The planned data science workflow is:

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

Initial supervised models planned for comparison:

- Dummy Classifier
- Logistic Regression
- Random Forest
- Gradient Boosting

Complementary unsupervised analysis:

- K-Means

Because heavy-rainfall events may be much less frequent than non-events, model evaluation will not rely on accuracy alone. Candidate metrics include:

- Precision
- Recall
- F1-score
- ROC-AUC
- PR-AUC
- Confusion Matrix

The final choice of metrics may be adjusted after the target distribution is inspected.

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

🚧 **Project under active development.**

### Roadmap

- [ ] Add and document the INMET dataset
- [ ] Audit dataset structure and quality
- [ ] Check missing timestamps and duplicated observations
- [ ] Perform exploratory data analysis
- [ ] Define the operational heavy-rainfall threshold
- [ ] Build forecasting targets for +1h to +6h
- [ ] Establish baseline models
- [ ] Train supervised ML models
- [ ] Compare performance across forecasting horizons
- [ ] Analyze meteorological patterns using clustering
- [ ] Create a prediction API
- [ ] Develop an application prototype

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

Environment setup:

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
pip install -r requirements.txt
```

## Disclaimer

This repository is a research prototype.

It **must not be used as an official weather warning or emergency alert system**. For severe-weather warnings and emergency guidance, users should rely on official meteorological and civil-defense services.

## License

A project license has not yet been selected. Before adding a license, the research group should align on how the academic code and data may be reused.
