# Software productionization validation — 2026-10-11

## Authorized Git publication check — 2026-10-13

The user authorized a new named commit and push of the existing checkpoint plus
all completed software/documentation work. The pre-publication suite passed
38 tests without skips in the clean runtime in 13.063 seconds. Runtime version
checking, `pip check`, compilation and `git diff --check` also passed.
PDF relocation to `docs/articles/` preserves its SHA-256 and 27-page content;
the article and all nine protected model/scientific files match recorded hashes.
No production training or model/threshold selection was repeated.

The pending-file and no-push descriptions below are the original 11/10/2026
validation snapshot, retained as history. They are superseded for Git permission
by the explicit publication authorization recorded in `docs/PROJECT_HANDOFF.md`.
Current branch synchronization is verified with Git after publication.

The authorized local checkpoint is **7279eed** on `main`, containing temporal
correction, revalidation and final artifact generation. Work described here
follows that checkpoint and is left **unstaged/uncommitted**, with no push.
Scientific choices/results remain those of [README.md](README.md), not the
historical tables farther down the original handoff.

## Delivered stages

| Stage | Delivered and checked |
|---|---|
| 1. Inference | `src/models/predict.py`, six artifacts loaded once, fixed thresholds, batch/single-row API and CLI |
| 2. Tests | Feature ordering, numeric completeness, extra future/target columns, malformed metadata, threshold equality, CLI and direct artifact parity |
| 3. Reusable source | Shared schema/factory, causal hourly-history builder, audited CSV loader and safe temporal-selection helpers |
| 4. Environment | Recorded Python, runtime/transitive version pins, separate notebook requirements, read-only environment checker |
| 5. Documentation | README, architecture, inference contracts, application instructions and current handoff |
| 6. Prototype | Local HTTP server, Portuguese responsive UI, seven editable UTC hours, examples, six forecasts and JSON export |

The factory/temporal-selection extraction preserves original function bodies,
parameters and compatibility imports. No production model fit or selection
rerun was executed. Existing regression tests fit **synthetic** temporary fixtures
only. No new web framework/test dependency was introduced.

## Checks

The full suite passed **38 tests, without skips** in the original environment:
7 training, 4 temporal selection, 5 features, 11 inference, 3 environment and
8 application tests. Runtime and development versions matched the recorded pins;
`pip check` found no broken requirements. A clean `.venv-repro` runtime install
also passed all 38 tests without skips, its version check and `pip check`. All
eleven runtime packages match the original recorded environment. The clean
environment is ignored and retained locally. Full evidence is recorded in
[productionization_checks.json](productionization_checks.json).

Existing-model inference reproduced **all six frozen 2021 metric rows** to
absolute tolerance **1e-12**, with exact sample/positive/confusion counts. This
is a regression check, not a new model-selection exercise. Feature parity uses
40+ timestamps across the effective dataset. Direct score equivalence allows
1e-14 tolerance for floating-point summation, while threshold decisions remain
the exact `score >= threshold` operation.

Browser QA used the real models on localhost:

- Synthetic input produced six scores and correct forecast timestamps.
- Current-rainfall historical input produced alerts at +1h and +5h; examples
  were chosen using current measurements only, without inspecting future labels.
- Introducing a gap caused HTTP 400, a visible input error and cleared results.
- Downloaded JSON contained all six horizons and frozen thresholds; the browser
  saved this test export to the user's Downloads directory.
- Desktop width 1265 and mobile width 412 were checked. A mobile grid overflow
  was corrected; document width equaled viewport width afterward. Horizontal
  scrolling is confined to the observation table. Console inspection showed no
  JavaScript errors in the exercised flows. Temporary viewport overrides were reset.
- Preview servers on ports 8000/8001 were stopped after QA. No service remains
  running in the background. The app can be restarted using its documented command.

![Synthetic demonstration](../figures/application-prototype.jpg)

Integrity checks compare SHA-256 before/after for all six joblibs, model metadata,
frozen configuration JSON and corrected result CSV; they also verify the dataset
against its recorded SHA-256. The JSON records the actual checks. No historical
CSV, notebook, scientific figure, hyperparameter or threshold was rewritten.
AGENTS/README/handoff received explicit software-status updates only.
AST comparison also confirms the factory, training function and three extracted
data helpers are unchanged from checkpoint 7279eed apart from their location.

## Commands used

From the repository root (the existing interpreter is `.venv-1/Scripts/python.exe`):

```powershell
git status --short
git diff --stat
git diff --check
& .\.venv-1\Scripts\python.exe -m src.check_environment --development
& .\.venv-1\Scripts\python.exe -m pip check
& .\.venv-1\Scripts\python.exe -W "ignore::UserWarning:sklearn.utils.parallel" -m unittest discover -s tests -p test_predict.py -v
& .\.venv-1\Scripts\python.exe -W "ignore::UserWarning:sklearn.utils.parallel" -m unittest discover -s tests -p test_app.py -v
& .\.venv-1\Scripts\python.exe -m unittest discover -s tests -p test_environment.py -v
& .\.venv-1\Scripts\python.exe -W "ignore::UserWarning:sklearn.utils.parallel" -m unittest discover -s tests -v *> productionization_tests.log
& .\.venv-1\Scripts\python.exe -m compileall -q src tests app
& .\.venv-1\Scripts\python.exe -W "ignore::UserWarning:sklearn.utils.parallel" -u -m app.server --port 8000
& .\.venv-1\Scripts\python.exe -W "ignore::UserWarning:sklearn.utils.parallel" -u -m app.server --port 8001
& .\.venv-1\Scripts\python.exe -m venv .venv-repro
& .\.venv-repro\Scripts\python.exe -m ensurepip --upgrade --default-pip
& .\.venv-repro\Scripts\python.exe -m pip install --disable-pip-version-check --index-url https://pypi.org/simple -r requirements.txt
& .\.venv-repro\Scripts\python.exe -m src.check_environment
& .\.venv-repro\Scripts\python.exe -m pip check
& .\.venv-repro\Scripts\python.exe -W "ignore::UserWarning:sklearn.utils.parallel" -m unittest discover -s tests -v *> clean_environment_tests.log
```

The checkpoint used explicit staging of 25 reviewed files followed by
`git commit -m 'fix: enforce temporal label boundaries and serialize final models'`,
as separately authorized by the user. No later staging/commit occurred.

Read-only inspection used `rg`, `Get-Content`, directory listings, library metadata,
SHA-256 comparison, and normal browser actions through the Sites local-preview
workflow. CLI success/error paths are executed by automated subprocess tests.

## Issues found and corrected

Local network connections were blocked in the sandbox (WinError 10013); automated
HTTP tests and the accessible preview ran with approved localhost access. The
isolated environment bootstrap also needed approved access to temporary files.
No automatic approval rejection occurred. The first preview inside the sandbox
timed out; the subsequent accessible localhost server was tested successfully.

An exact-float application test differed by about 2e-16 from parallel RF
summation; it now uses the justified 1e-14 comparison tolerance. This changes
neither model outputs nor thresholds. The initial clean dependency resolver
selected newer Narwhals; all runtime transitive packages were then explicitly
pinned to versions in the original validated environment.

The existing environment sometimes emits nonfatal Python executable-location
and scikit-learn parallel-configuration warnings. A scoped CLI warning filter
reduces, but does not always eliminate, parallel warnings. Installed libraries
and estimator `n_jobs` were not patched to silence them. Scientific regression
checks pass despite those warnings. Git reports its existing LF/CRLF policy.

## Remaining scope

The app is a local academic demonstration, without live ingestion, public hosting,
authentication or official alerting. Model scores are uncalibrated. Binary artifacts
and datasets are ignored and must be generated/obtained locally for a fresh clone.
Notebook tools have direct pins, not a full transitive lock. Original download
URLs/access dates/data usage metadata, project licensing, contributor attribution
and final academic text remain pending. These are not resolved by inventing data
or by changing the already validated scientific results.

Next checkpoint requires user review and authorization. The current handoff and
machine-readable checks record progress; no new Git write is automatic.

## Files created or modified

All changes below are pending after checkpoint 7279eed; nothing is staged.

| Git state | File |
|---|---|
| Modified | `.gitignore` |
| Modified | `AGENTS.md` |
| Modified | `README.md` |
| Modified | `app/README.md` |
| Modified | `docs/PROJECT_HANDOFF.md` |
| Modified | `docs/architecture.md` |
| Modified | `docs/validation/README.md` |
| Modified | `requirements.txt` |
| Modified | `src/README.md` |
| Modified | `src/models/train_final_models.py` |
| Modified | `tests/README.md` |
| Created | `.python-version` |
| Created | `app/server.py` |
| Created | `app/static/app.js` |
| Created | `app/static/index.html` |
| Created | `app/static/styles.css` |
| Created | `docs/INFERENCE.md` |
| Created | `docs/figures/application-prototype.jpg` |
| Created | `docs/validation/productionization.md` |
| Created | `docs/validation/productionization_checks.json` |
| Created | `requirements-dev.txt` |
| Created | `src/check_environment.py` |
| Created | `src/data/json_input.py` |
| Created | `src/data/model_dataset.py` |
| Created | `src/features/build_features.py` |
| Created | `src/features/schema.py` |
| Created | `src/models/config.py` |
| Created | `src/models/predict.py` |
| Created | `tests/test_app.py` |
| Created | `tests/test_environment.py` |
| Created | `tests/test_features.py` |
| Created | `tests/test_predict.py` |

Generated locally and ignored: `.venv-repro/`, Python caches and test/install logs.
The six production model artifacts and metadata remain unchanged and ignored.
