# Tests

Automated tests for reusable preprocessing, feature engineering, training, and prediction code.

Run the full suite with standard-library
unittest (no additional dependency):

```powershell
python -m unittest discover -s tests -v
```

Checks cover all six horizons and all three year boundaries, horizon eligibility,
exclusion of reserved-period labels, rejection of malformed/incomplete inputs,
pre-2021 selection, training-only scalers, metadata and actual six-model joblib
serialization. Synthetic artifacts are created and cleaned inside temporary
directories under `tests/`, without touching the production models.

`test_predict.py` checks threshold equality, batch order, input validation and
artifact consistency, comparing read-only predictions with all six saved models.
`test_features.py` checks causal lags/sums/changes, UTC/leap-year cycles, invalid
history and 40+ feature-parity samples across the dataset. `test_environment.py`
checks valid versions and explicit mismatch errors.

`test_app.py` uses actual localhost HTTP requests to verify status/error contracts,
plus read-only integration of raw historical observations and existing models.
The inference suite also exercises the CLI and reproduces the six frozen 2021
metric rows to tolerance 1e-12, without training or rewriting result files.

Integration tests explicitly skip if ignored local models/data are absent. Supply
these files and verify no skips to validate complete integration. No test overwrites
the production artifacts.

Citizen application tests cover official CSV units/provenance, missing values,
station refusal, latest partial records, gaps, future timestamps, runtime
freshness, expired horizons and historical isolation. Optional Web Push tests
check persistent keys, revocation, actual payload encryption/signing with mocked
HTTP delivery, provider/private-IP restrictions, redirect refusal, deduplication,
expiry and retry/removal behavior. Install `requirements-webpush.txt` to run
these tests without skips. They never send real notifications to a person.

The service worker's independent tests use Node's built-in runner:

```powershell
node --test tests/test_service_worker.cjs
```

They check current/expired/malformed notification handling, offline API exclusion
and safe notification-click navigation. Node is only needed for frontend checks;
the application itself runs with Python and a browser.
