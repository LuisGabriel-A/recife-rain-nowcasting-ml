# Application

A functional local web prototype uses the six existing models through
`src.models.predict.RainPredictor`. The server uses Python's standard library;
the UI uses plain HTML/CSS/JavaScript, with no CDN or new web dependency.

## Run

From the repository root, with the pinned environment and trusted local model
artifacts available:

```powershell
& .\.venv-1\Scripts\python.exe -m src.check_environment
& .\.venv-1\Scripts\python.exe -m app.server --port 8000
```

Use your own validated `.venv` interpreter if applicable. Open
[http://127.0.0.1:8000](http://127.0.0.1:8000). Stop with Ctrl+C. `--port` allows
a different local port; `--model-dir` is an operator-controlled trusted directory.
Missing/incompatible artifacts cause an explicit startup error; no automatic
training occurs. This is a localhost demonstration server, not public hosting.

## Demonstration

1. Select the synthetic example or a historical dry/rain scenario.
2. Edit seven consecutive hours, with all times explicitly shown as UTC.
3. Click **Consultar os seis horizontes**.
4. Inspect each score, its frozen threshold, alert status and forecast timestamp.
5. Expand **Entrada e saída JSON** or download the result.

Changing input clears stale results. Fields are disabled while a request is in
flight; incomplete/invalid histories produce an error without new predictions.
On small screens the history table scrolls inside its panel.

The synthetic example is clearly labeled. Historical examples are selected from
the local ignored model dataset using **current observed rainfall only**, not
future labels/model scores. Their seven-hour observations are loaded at startup;
no raw historical values are redistributed with source code. They can include
training observations and are demonstrations, not independent performance tests.
If the dataset is absent, synthetic/manual inference still works; historical
options are omitted. The prototype does not ingest live weather or issue official
alerts. Scores are uncalibrated; inactive alerts do not establish safety.

## HTTP interface

| Method/path | Contract |
|---|---|
| GET / | Application UI |
| GET /api/health | Loaded station, six horizons and actual artifact thresholds |
| GET /api/examples | Historical examples if the local dataset is present |
| POST /api/predict | Exactly one JSON key: observations or features |

`observations`: 7–168 records of timestamp plus four meteorological fields;
`features`: one 20-feature object or a batch up to 100 objects. The body is
limited to 65,536 bytes. Invalid input returns HTTP 400, oversized bodies 413,
wrong content types 415, unknown routes 404. The server exposes only three static
files and these endpoints, not workspace files/model uploads.
Duplicate JSON fields and NaN/Infinity constants are rejected. Displayed scores
are rounded to three decimals; decisions and exported JSON use full precision.

Responses include A301, prediction time (history input only), operational severe
rain threshold, `score_is_calibrated=false`, and six predictions per sample.
Each prediction has score, threshold, alert, model family and forecast time
(null for precomputed features without a timestamp). Input/output field details
are in [INFERENCE.md](../docs/INFERENCE.md).

For the synthetic feature file from that guide:

```powershell
$featureSample = Get-Content -Raw features.tmp | ConvertFrom-Json
$requestPayload = @{ features = $featureSample } | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/predict -Method Post -ContentType application/json -Body $requestPayload
```

Eight automated application tests passed, including actual HTTP requests and
read-only integration with existing artifacts. Browser QA covered synthetic and
historical forecasts, temporal-gap rejection, JSON download, and desktop/mobile
layouts. Preview servers were stopped after QA. [Validation record](../docs/validation/productionization.md).

![Prototype with synthetic input](../docs/figures/application-prototype.jpg)
