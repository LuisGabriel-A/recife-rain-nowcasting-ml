# Architecture

This document will evolve with the project.

## Initial research pipeline

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
 Mobile application
```

## Design principle

The project must keep the research pipeline reproducible and separate experimentation from reusable production code:

- `notebooks/`: investigation and documented experiments;
- `src/`: reusable preprocessing, features, training, prediction, and evaluation code;
- `data/`: source and generated datasets;
- `models/`: generated model artifacts;
- `app/`: future application/API integration;
- `tests/`: automated validation of reusable code.
