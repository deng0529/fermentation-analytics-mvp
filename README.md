# Fermentation Analytics MVP

The Fermentation Analytics MVP uses Streamlit for replay, spectral calibration, and forecast evaluation. Turso stores the versioned spectra and published results. [index.html](index.html) is the original HTML prototype.

## Windows PowerShell setup

Open PowerShell in the project folder. Use Python 3.12.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configure Turso and import the spectral datasets

Set `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` in the project-root `.env` or in the environment of the process that runs Python. The existing `Fermentation_TURSO_DATABASE_URL` and `Fermentation_TURSO_AUTH_TOKEN` names also work. The Streamlit app can also read either pair as top-level keys in `.streamlit/secrets.toml`. The CLI reads environment variables and `.env`. Keep both credential files local.

Use the URL of the Fermentation Analytics database and a database token with write access. From the project root, run:

```powershell
.\.venv\Scripts\python.exe -m spectral_store
```

This applies the migrations, imports the active NIR snapshot if missing, and reads it back from Turso. A missing snapshot requires write access and access to its original source. Historical snapshots can be accessed by passing an explicit `--dataset` option.

## Migrate and publish results

With the verified NIR snapshot in Turso and a write-capable token, run:

```powershell
.\.venv\Scripts\python.exe backfill_results.py migrate
.\.venv\Scripts\python.exe backfill_results.py backfill
```

The results CLI also accepts top-level keys in `.streamlit/secrets.toml`. Backfill fits the two Model 1 experiments and Model 2, checks the portable inference equations, builds all five replay versions, and publishes the bundle in one transaction. A repeat of an already published release reports the existing counts. The app can use a read-only token after publication. To publish a changed model or scenario definition, update the result release identifier in `results_store.py` and publish the new release. Earlier rows remain available in Turso.

## Run the app

Launch from the same folder. Streamlit reruns the app when a watched source file changes.

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address=127.0.0.1 --server.port=8501 --server.runOnSave=true
```

Open [http://localhost:8501](http://localhost:8501).

## Review workflows

- **Data Explorer** is the landing page. It shows the published NIR tables from Turso. The initial NIR import uses R-universe.
- **Preprocessing & Feature Selection** shows each target’s inputs, output, source preprocessing, and evaluation split. NIR uses all 235 published channels and a shared split of 116 training, 25 validation, and 25 test pairs.
- **Model Training & Validation** reads the published ethanol PLS and glucose RBF SVR experiments. It shows fitted equations, parameters, candidates, metrics, and held-out predictions.
- **Batch Monitor** has three ethanol-only replay modes with manual navigation and Play / Pause at one simulated hour per second. The three direct synthetic cases use saved Ridge forecasts and simulated endpoint references. The public NIR replay shows PLS estimates and separate calibration validation on a simulated two-minute clock, with discharge schedule unknown. The synthetic spectral batch uses illustrative spectra and the saved PLS → Ridge path with a simulated 36-hour schedule, a final reference, and a same-trajectory direct-input comparison. Both 36-hour replays issue forecasts at hours 2–35 and mark hour 30. The source selectors and playback clock use session state.

## Code and tables

| Files | Responsibility |
| --- | --- |
| `app.py`, `batch_monitor.py` | Page routing, renderers, and replay clock controls |
| `example_data.py`, `replay_data.py` | Showcase inputs, timestamp preparation, and illustrative spectra |
| `model_1a.py`, `nir_calibration.py`, `fitted_state.py` | Calibration fitting and portable inference equations |
| `model_2.py` | Shared causal features, synthetic splits, Ridge fitting and evaluation |
| `turso_database.py`, `spectral_store.py`, `results_store.py` | Turso transport, spectral snapshots, and versioned result reads and publication |
| `migrations/`, `backfill_results.py` | Idempotent schema and explicit backfill command |

`dataset_versions` identifies a source snapshot. `spectral_inputs`, `reference_outputs`, and `test_alignment` retain the original imports and links. Each `model_runs` row can reference a source snapshot and owns a `model_artifacts` row and multiple `model_metrics` and `model_predictions` rows. Each `replay_batches` row can reference a snapshot and a calibration and/or forecast run. `replay_observations` contains the replay clock, saved ethanol and a public-spectrum key or generated spectrum where applicable. `replay_forecasts` references the batch and Ridge run and stores the issue time, input path, three features and prediction.

## Seven-step scope

| Step | Work |
| --- | --- |
| 1 | Review the local Streamlit prototype. |
| 2 | Inspect the two public calibration datasets. Verify spectral features, units, reference values, sample pairing, preprocessing, batch IDs, and timestamps. |
| 3 | Import versioned datasets into Turso and read them in the app. Use TSV for inspection or export. |
| 4 | Use the imported channel inventory for feature selection and retain exact inputs in experiment records. |
| 5 | Fit and validate Model 1A calibration regressors using shared held-out samples. |
| 6 | Generate and validate synthetic Model 2 batches. Compare discharge regression with recent-trend extrapolation and report error by lead time, missed shortfalls, and false warnings. |
| 7 | Connect fitted results to the app and review the operator and engineering workflows. |
