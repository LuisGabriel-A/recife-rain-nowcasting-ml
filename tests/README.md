# Tests

Automated tests for reusable preprocessing, feature engineering, training, and prediction code.

Run the training and temporal-boundary regression checks with standard-library
unittest (no additional dependency):

```powershell
python -m unittest discover -s tests -v
```

Checks cover all six horizons and all three year boundaries, horizon eligibility,
exclusion of reserved-period labels, rejection of malformed/incomplete inputs,
pre-2021 selection, training-only scalers, metadata and actual six-model joblib
serialization. Synthetic artifacts are created and cleaned inside temporary
directories under `tests/`, without touching the production models.
