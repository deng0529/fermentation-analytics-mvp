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

## Data Sources & References

### Experimental NIR data used by Model 1

The **NIR data** (`chemometrics::NIR`) contain 166 experimental fermentation-mash samples. Each record pairs 235 published first-derivative NIR channels (1115–2285 nm) with reference glucose and ethanol concentrations in g/L. The research was conducted by Liebmann, Friedl, and Varmuza at TU Wien (Vienna University of Technology). Peter Filzmoser maintains the distributing R package. The importer reads the two R-universe JSON components, validates and pairs rows in source order, and stores a versioned Turso snapshot. [Dataset entry](https://search.r-project.org/CRAN/refmans/chemometrics/html/NIR.html) · [R-universe JSON](https://filzmoserp.r-universe.dev/chemometrics/data/NIR/json) · [CRAN package](https://cran.r-project.org/package=chemometrics)

Suggested research citation. Liebmann, B., Friedl, A., & Varmuza, K. (2009). Determination of glucose and ethanol in bioethanol production by near infrared spectroscopy and chemometrics. *Analytica Chimica Acta, 642*(1–2), 171–178. [DOI 10.1016/j.aca.2008.10.069](https://doi.org/10.1016/j.aca.2008.10.069)

Data Explorer displays the source derivative spectra and paired measurements. The calibration code uses one fixed row split for ethanol PLS and glucose RBF SVR. It fits on 116 rows, uses 25 validation rows for candidate selection and reports errors on 25 held-out rows. The public NIR replay assigns two-minute intervals to rows in source order and shows saved Model 1 predictions. The assigned clock supplies no verified trajectory or discharge schedule.

**Licence and reuse.** CRAN declares GPL (≥ 3) for the R package. Licence status for the underlying experimental data has not been confirmed separately. Public download, permission for internal reuse, permission to display or redistribute records, and permission for commercial use are separate questions. The public app exposes source spectra and references in tables and plots. Confirm the applicable terms with the package maintainer and original data rights holders, including the scope of public display, downloads, commercial reuse and exports or artifacts that may contain source-derived information. Record the permission and any required notices before publishing this update. If permission is unavailable, agree on a separately scoped restricted-access or replacement dataset plan.

### Historical ATR-FTIR import

**The Fermentation Dataset** is distributed by `chemotools`, maintained by Pau Cabaneros Lopez. The data documentation describes synthetic calibration spectra and a test sequence acquired during fermentation. The import validates 21 calibration spectra and references, 1,629 test spectra and 34 test reference rows. It preserves the package inputs and stores an approximate nearest-time alignment. The retained snapshot is available through the explicit legacy import/read path and is outside the current UI, Model 1, and Model 2. The app-specific counts describe its pinned import, which can differ from the documentation’s rounded or version-independent description. [Dataset documentation](https://chemotools.org/learn/datasets.html#the-fermentation-dataset) · [Pinned package release](https://pypi.org/project/chemotools/0.5.0/)

Suggested associated research citation. Cabaneros Lopez, P., Udugama, I. A., Thomsen, S. T., Roslander, C., Junicke, H., Iglesias, M. M., & Gernaey, K. V. (2021). Transforming data to information: A parallel hybrid model for real-time state estimation in lignocellulosic ethanol fermentation. *Biotechnology and Bioengineering, 118*(2), 579–591. The research team includes the Technical University of Denmark, University of Copenhagen, Lund University, and Universidade de Santiago de Compostela. [DOI 10.1002/bit.27586](https://doi.org/10.1002/bit.27586) · [DTU research record](https://orbit.dtu.dk/en/publications/transforming-data-to-information-a-parallel-hybrid-model-for-real/)

**Licence and reuse.** The package declares MIT for its software, and the associated research article is published under CC BY 4.0. Licence status for the underlying distributed calibration and test data files has not been confirmed separately. Confirm dataset reuse, redistribution and commercial terms with the provider before exposing the historical snapshot or distributing its files.

### Simulation, processed inputs, and results

| Data | Origin and role |
| --- | --- |
| Direct synthetic showcase replays | Project-generated fixtures in `example_data.py`. The readings and endpoint references illustrate three scenarios and are excluded from fitting, tuning, and aggregate evaluation. |
| Synthetic Model 2 evaluation data | The separate seeded generator in `model_2.py` produces 240 training, 80 validation, and 80 held-out batches. The Ridge inputs are latest ethanol, the two-hour ethanol slope, and time remaining. Ridge and trend extrapolation are compared against simulated endpoints. |
| Synthetic spectral batch | `replay_data.py` generates illustrative, source-derived spectra from averaged NIR training templates plus seeded noise and an assigned trajectory. It passes those spectra through PLS and Ridge and reports a separate example comparison. Its simulated endpoint and results are outside both models’ training, tuning, and aggregate evaluation. |
| Saved analytical outputs | Turso stores predictions, fitted artifacts and evaluation summaries separately from measured and simulated references. Model 1 held-out errors concern sample-level calibration. Model 2 aggregate scores concern simulated discharge predictions. |

Simulated performance does not establish accuracy on real industrial fermentation batches. The project developed the UI, snapshot and feature workflows, integration of fitted models, replay and monitoring logic, and visual reporting. It uses established PLS, RBF SVR and Ridge estimators from [scikit-learn](https://scikit-learn.org/), with [Streamlit](https://streamlit.io/), [Plotly](https://plotly.com/python/), [Altair](https://altair-viz.github.io/), pandas and NumPy. External research, data and software remain attributed to their providers.

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
