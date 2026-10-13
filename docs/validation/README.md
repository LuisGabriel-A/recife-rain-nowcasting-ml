# Temporal label-boundary correction — 2026-10-11

Software follow-up: inference, shared causal features, pinned dependencies and
the local application are now implemented. See [productionization.md](productionization.md)
for current software checks. This report retains the scientific correction and
historical record from checkpoint `7279eed`; its results/configurations are unchanged.

The user explicitly authorized this correction after an audit found that the
original notebooks split samples by the observation timestamp `t` only. The last
`h` eligible observations of each year had `target_hh` labels derived from the
following year. Missing targets and missing measurements remain missing.

The corrected rule for **every training and validation partition** is:

```text
partition_start <= observation_time
observation_time + forecast_horizon < partition_end
eligible_final_Xh == True
```

The expanding folds remain train 2018 / validate 2019 and train 2018–2019 /
validate 2020. Final fitting uses 2018–2020 with both observation and target
timestamps before 2021. Earlier year boundaries inside an expanding training
window need no exclusion once both sides belong to that training window.

## Removed samples and events

Each cell below gives the number of samples removed. **Zero positive labels were
removed in every cell.** The table describes separate fitting/validation uses;
overlapping expanding windows must not be added as unique observations.

| Partition | +1h | +2h | +3h | +4h | +5h | +6h |
|---|---:|---:|---:|---:|---:|---:|
| Fold 1 training: 2018, boundary 2018/2019 | 1 | 2 | 3 | 4 | 5 | 6 |
| Fold 1 validation: 2019, boundary 2019/2020 | 1 | 2 | 3 | 4 | 5 | 6 |
| Fold 2 training: 2018–2019, boundary 2019/2020 | 1 | 2 | 3 | 4 | 5 | 6 |
| Fold 2 validation: 2020, boundary 2020/2021 | 1 | 2 | 3 | 4 | 5 | 6 |
| Final training: 2018–2020, boundary 2020/2021 | 1 | 2 | 3 | 4 | 5 | 6 |

[temporal_boundary_audit.csv](temporal_boundary_audit.csv) records the original
and corrected sample/event counts for all 30 partition/horizon combinations.

## Selection procedure

Even though all removed labels were negative, retraining changes fitted models,
bootstrap samples, scaling, probability rankings and threshold decisions. Both
hyperparameter selection and OOF threshold selection therefore had to be repeated.

The original notebook 10 grids are retained: Logistic Regression `C` in
`[0.01, 0.1, 1.0, 10.0]`; Random Forest `max_depth` in `[4, 8, None]` crossed with
`min_samples_leaf` in `[1, 10]`, using 300 estimators. Both families retain their
documented class weights and `random_state=42`. Logistic Regression retains
`max_iter=3000` and a training-only StandardScaler pipeline.

Parameters **and model families** are selected by mean validation Average
Precision. Thresholds maximize F1 over concatenated 2019–2020 OOF predictions,
using the original `np.arange(0.01, 1.00, 0.01)` grid and recall/precision tie
breaks. Grid order resolves exact configuration AP ties. Selection rejects any
2021 observation and freezes all six choices before test evaluation.

Notebook 10 also contains a table ranking the families by **2021 test F1**. That
table is unsuitable for selection. The original documented family choices happen
to agree with the rounded pre-2021 validation AP values displayed in that notebook;
the corrected implementation makes the pre-2021 selection explicit and saves
unrounded evidence.

## Frozen configurations after correction

All Random Forest models retain 300 estimators, `balanced_subsample`,
`random_state=42`, and `n_jobs=-1`. Logistic Regression retains `C=0.01`,
`balanced`, `max_iter=3000`, `random_state=42`, and StandardScaler in its pipeline.

| Horizon | Historical family / threshold | Corrected family / threshold | Corrected RF depth / leaf |
|---|---|---|---|
| +1h | Logistic Regression / 0.99 | Logistic Regression / 0.99 | — |
| +2h | Random Forest / 0.13 | Random Forest / 0.06 | None / 10 |
| +3h | Random Forest / 0.77 | Random Forest / 0.78 | 4 / 1 |
| +4h | Logistic Regression / 0.94 | Random Forest / 0.79 | 4 / 10 |
| +5h | Logistic Regression / 0.85 | Logistic Regression / 0.85 | — |
| +6h | Random Forest / 0.57 | Random Forest / 0.67 | 8 / 1 |

The +4h AP comparison is close: Random Forest 0.016180918 versus Logistic
Regression 0.016147845 (see the unrounded CSV). No change is made in response
to its lower 2021 performance. The +5h alternate RF configuration also changed
from leaf 1 to leaf 10, but it was not selected for production.

The final corrected training counts are 25,585 / 25,569 / 25,552 / 25,538 /
25,525 / 25,513 for +1h through +6h, respectively. Positive counts remain
70 / 70 / 70 / 70 / 69 / 69. The test counts remain 7,248 / 7,246 / 7,244 /
7,242 / 7,239 / 7,237, with 38 positive labels per horizon.

## Historical versus corrected 2021 results

Every cell below is **historical → corrected**. AP is Average Precision.

| Horizon | Precision | Recall | F1 | CSI | AP | ROC-AUC |
|---|---|---|---|---|---|---|
| +1h | 0.170 → 0.170 | 0.447 → 0.447 | 0.246 → 0.246 | 0.140 → 0.140 | 0.225 → 0.225 | 0.945 → 0.945 |
| +2h | 0.056 → 0.034 | 0.395 → 0.684 | 0.098 → 0.064 | 0.051 → 0.033 | 0.076 → 0.066 | 0.866 → 0.863 |
| +3h | 0.090 → 0.100 | 0.526 → 0.474 | 0.154 → 0.165 | 0.083 → 0.090 | 0.071 → 0.069 | 0.898 → 0.897 |
| +4h | 0.097 → 0.073 | 0.368 → 0.289 | 0.153 → 0.117 | 0.083 → 0.062 | 0.075 → 0.063 | 0.897 → 0.878 |
| +5h | 0.038 → 0.038 | 0.526 → 0.526 | 0.071 → 0.071 | 0.037 → 0.037 | 0.049 → 0.049 | 0.861 → 0.861 |
| +6h | 0.032 → 0.042 | 0.237 → 0.132 | 0.056 → 0.064 | 0.029 → 0.033 | 0.022 → 0.023 | 0.821 → 0.822 |

| Horizon | True positives | False positives | False negatives | True negatives |
|---|---|---|---|---|
| +1h | 17 → 17 | 83 → 83 | 21 → 21 | 7127 → 7127 |
| +2h | 15 → 26 | 254 → 747 | 23 → 12 | 6954 → 6461 |
| +3h | 20 → 18 | 202 → 162 | 18 → 20 | 7004 → 7044 |
| +4h | 14 → 11 | 131 → 139 | 24 → 27 | 7073 → 7065 |
| +5h | 20 → 20 | 504 → 504 | 18 → 18 | 6697 → 6697 |
| +6h | 9 → 5 | 272 → 113 | 29 → 33 | 6927 → 7086 |

The primary +1h result remains strongest overall among the frozen six models.
Its exact AP changes from 0.22478624166832795 to 0.2247870421761081;
use the CSV for unrounded metrics. Large changes in some RF outputs are possible
even when only a few negative rows are removed: a changed sample count changes
seeded bootstrap draws, and threshold selection changes which scores yield alerts.

These comparisons combine the boundary correction and the required reselection;
they do not isolate a causal effect of a single removed observation. Candidate
family test results are deliberately not used to revise the frozen selection.

Machine-readable evidence:

- [corrected_grid_results.csv](corrected_grid_results.csv): 60 configurations,
  each with two fold scores (120 fitted candidates).
- [corrected_validation_selection.csv](corrected_validation_selection.csv):
  12 within-family winners, selected thresholds and OOF metrics.
- [validated_configurations.json](validated_configurations.json): six frozen
  production configurations and the source dataset fingerprint.
- [corrected_final_evaluation_results.csv](corrected_final_evaluation_results.csv):
  corrected selected-model metrics on the fixed 2021 test.
- [final_results_comparison.csv](final_results_comparison.csv): full-precision
  historical/corrected comparison for all six horizons.

## Historical results

The original CSVs are preserved byte-for-byte under [history/](history/):
`final_evaluation_results.csv`, `tuned_model_results.csv`, and
`threshold_optimized_results.csv`. They have the label-boundary limitation
described above and must be cited as historical experimental results.

The original notebooks, their stored results and figures remain historical
evidence. Original processed result files are not overwritten. Corrected tables
are separate files in this directory. No selection uses the recalculated 2021
metrics; this is an explicitly disclosed correction of an already inspected
historical test, not a newly collected independent holdout.

## Reproduction

From the repository root, with the dataset available locally:

```powershell
python -m src.evaluation.revalidate_temporal_boundaries
python src/models/train_final_models.py
python -m unittest discover -s tests -v
```

Revalidation fits 120 candidate/fold models and then six selected final models.
It writes the grid scores, family selections, frozen configurations, corrected
test metrics and historical comparison. The training command uses the frozen
configurations, reproduces six models, reloads each joblib and verifies that
serialization preserves probabilities.

The validation environment was Python 3.14.6, NumPy 2.5.3, pandas 3.0.6,
scikit-learn 1.9.1, SciPy 1.18.1 and joblib 1.6.0. Model metadata records the
training environment, source dataset SHA-256, ordered features, thresholds and
latest observation/target timestamps. Numerical differences can arise with other
library versions; the original requirements file does not pin versions.

## Validation performed

All 11 automated tests passed. The source files also passed `compileall` and
`git diff --check`. The production artifacts were checked independently after
serialization:

- All six metadata records match their joblib bundles and their pre-2021 AP
  selection records; positive probability corresponds to class 1.
- Every model uses exactly the ordered 20 features. Both fitted LR scalers have
  means and sample counts equal to their eligible training data only.
- No observation or label used for final fitting is in 2021. The latest retained
  target timestamp is `2020-12-31 23:00 UTC` for every horizon.
- Saved model probabilities are finite and in `[0, 1]`; their 2021 metrics
  reproduce the corrected CSVs to numerical tolerance `1e-12`.
- The source dataset has a continuous hourly grid. All six targets exactly match
  rainfall at `t+h`; missing future precipitation remains a missing target.
- Every derived feature matches a recalculation from current/past observations,
  and all eligibility flags match feature/target completeness.
- Historical CSVs are byte-identical to the original processed results.
  Historical notebook code, outputs and metadata are unchanged; only an explicit
  introductory historical-status cell was added.

The machine-readable verification is [artifact_validation.json](artifact_validation.json).

Actual training/test commands used the existing notebook environment:

```powershell
& .\.venv-1\Scripts\python.exe -W "ignore::UserWarning:sklearn.utils.parallel" -u -m src.evaluation.revalidate_temporal_boundaries *> revalidation.log
& .\.venv-1\Scripts\python.exe -W "ignore::UserWarning:sklearn.utils.parallel" -u src/models/train_final_models.py *> training.log
& .\.venv-1\Scripts\python.exe -W "ignore::UserWarning:sklearn.utils.parallel" -m unittest discover -s tests -v *> tests.log
& .\.venv-1\Scripts\python.exe -m compileall -q src tests
git diff --check
git status --short
git check-ignore models/model_metadata.json models/model_1h.joblib models/model_6h.joblib
```

Additional read-only inspection used `Get-Content`, `Get-ChildItem`, `rg --files`,
`git branch --show-current`, `git remote -v`, `git diff --stat`, `git diff --numstat`,
`Get-FileHash`, and a GitHub repository metadata lookup. Inline Python audits
checked all boundary counts, reconstructed features/targets, verified model
metadata/scalers/metrics, and compared original notebook JSON obtained using
`git show HEAD:<notebook>`.

Initial tests hit the sandbox's system temporary-directory restriction; test
fixtures were moved into managed temporary directories under `tests/` and cleaned
automatically. The environment emitted a nonfatal Python executable-location
warning. A narrowly scoped command-line warning filter avoided repeated
scikit-learn parallel-worker warnings without changing estimators or dependencies.
Git also reports its existing LF/CRLF normalization policy. No new dependency,
commit, push or remote write was introduced.

## Files created or changed

Created source/tests:

- `src/models/train_final_models.py`
- `src/evaluation/revalidate_temporal_boundaries.py`
- `tests/test_train_final_models.py`
- `tests/test_temporal_revalidation.py`

Created validation evidence in this directory:

- `README.md`
- `temporal_boundary_audit.csv`
- `corrected_grid_results.csv`
- `corrected_validation_selection.csv`
- `validated_configurations.json`
- `corrected_final_evaluation_results.csv`
- `final_results_comparison.csv`
- `artifact_validation.json`
- `history/final_evaluation_results.csv`
- `history/tuned_model_results.csv`
- `history/threshold_optimized_results.csv`

Updated documentation: `AGENTS.md`, `docs/PROJECT_HANDOFF.md`, `README.md`,
`data/README.md`, `src/README.md`, and `tests/README.md`. Added historical-status notes to
`notebooks/08_baseline_models.ipynb`, `09_threshold_optimization.ipynb`,
`10_model_tuning.ipynb`, and `12_final_evaluation.ipynb`.

Generated locally and ignored by Git: `models/model_1h.joblib` through
`model_6h.joblib`, `models/model_metadata.json`, `revalidation.log`, `training.log`,
`tests.log`, and Python bytecode caches. Existing processed datasets/results and
original figures are unchanged.

Inference and app integration have not been implemented in this task. Dependencies
remain unpinned; changing library versions may change numerical results. The
corrected 2021 evaluation remains an already inspected historical holdout.
Original data-download URLs, access dates and usage metadata remain pending in
`data/README.md`; no provenance values were invented.
