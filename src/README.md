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

`features/schema.py` defines the ordered feature contract shared by all modules.
`features/build_features.py` creates the latest causal sample from at least seven
observed consecutive hours. `data/model_dataset.py` holds CSV validation and
temporal selection; `models/config.py` supplies the unchanged deterministic
factory and reads the authoritative frozen configuration JSON.

`models/predict.py` loads the six existing models once, checks metadata/environment,
and returns scores/alerts at fixed thresholds. It never calls fit.
`check_environment.py` verifies the Python/package pins without installing anything.

```powershell
python -m src.check_environment
python -m src.models.predict features.tmp
python -m unittest discover -s tests -v
```

See [the inference guide](../docs/INFERENCE.md). Training and reselection commands
above are explicit reproduction tools; routine inference does not need them.

`data/inmet_recent.py` imports the official A301 table CSV into private runtime
state with source hash/attestation. It converts decimal commas and missing-data
sentinels without filling values, and validates seven consecutive hours.
`models/alert_status.py` presents the existing decisions for citizens, rejecting
stale/future observations and expired forecast hours. These modules never change
the experimental dataset, fitted models or thresholds. The runtime supports
optional notifications through `app/webpush.py`; see [application setup](../app/README.md).
