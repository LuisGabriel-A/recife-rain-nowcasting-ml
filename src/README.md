# Source Code

`models/train_final_models.py` trains and serializes the six temporally validated
forecasting models using the fixed 20 features. It reads the frozen selection
record in `docs/validation/validated_configurations.json`, validates eligible
rows, purges labels crossing 2021 and fits scalers only inside training pipelines.

`evaluation/revalidate_temporal_boundaries.py` reproduces the authorized
correction across both expanding folds, repeats the original hyperparameter and
OOF threshold procedure, freezes the selected configurations, then evaluates the
fixed 2021 test. It preserves the original experimental results.

From the repository root:

```powershell
python src/models/train_final_models.py
python -m src.evaluation.revalidate_temporal_boundaries
```

Inference code is the next productionization task.
