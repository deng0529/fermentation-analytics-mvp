# Fermentation replay and Turso results

26 November 2026 · [Batch Monitor](http://127.0.0.1:8505/batch-monitor) · [Model Training & Validation](http://127.0.0.1:8505/training)

Report path `C:/Weihua/project/Fermentation Analytics MVP/FERMENTATION_REPLAY_AND_TURSO_REPORT.md`.

The Batch Monitor has three ethanol-only replay options. It loads saved observations and forecasts, verifies their parity on load, and uses the session clock to reveal only data released by the selected time. The Model Training & Validation page loads both saved Model 1 experiments, including fitted parameters, candidate comparisons, metrics, and the held-out points for its plots.

## Replay results and what they establish

### Synthetic batch replay

The three original showcase fixtures use their formula-generated ethanol readings directly. Each saved replay has 37 hourly observations and 34 Ridge forecasts from hour 2 to hour 35 for scheduled discharge at hour 36. The 130 g/L demo target comes from `example_data.TARGET`. The simulated final reference is the third value of the respective `example_data.BATCHES` tuple, released at hour 36. Warnings use the signed difference from the target.

| Scenario | Hour-30 forecast (g/L) | Hour-35 forecast (g/L) | Final reference (g/L) |
| --- | ---: | ---: | ---: |
| F-0607 · Shortfall | 127.286 | 115.221 | 120.400 |
| F-0608 · On target | 142.472 | 130.947 | 133.100 |
| F-0609 · Recovery | 141.242 | 129.757 | 131.300 |

F-0607 levels off below target, F-0608 levels off above target, and F-0609 rises past target late. The computed F-0609 forecast falls below target by hour 35 despite the simulated endpoint clearing it. These showcase errors are separate from the aggregate hold-out results.

### Model 1 spectral replay

The public `chemometrics::NIR` replay uses all 166 source rows in the stored order, from `R1 zaM 1` to `VM3_7z`. Two simulated minutes separate consecutive rows. The first and last timestamps are 0 and 330 minutes, giving a replay duration of 5 h 30 min. Saved ethanol estimates from the fitted 10-component PLS range across the source sequence, with first and last values **41.280347** and **88.067481 g/L**. The sequence has no verified batch chronology, schedule, or discharge assay. The page shows the scheduled discharge as Unknown and omits discharge forecasts and the demo target.

The separate Model 1 calibration evaluation uses the 25 held-out spectrum–assay pairs and displays signed error as estimated minus measured ethanol. Its **MAE is 1.062083 g/L** and **RMSE is 1.489760 g/L**. Those scores evaluate current concentration estimates. Independent factory spectra paired with assays would establish how the calibration transfers.

### Synthetic spectral batch

`SIM-NIR-01` has a simulated discharge schedule at hour 36, **1,081 spectra** at two-minute intervals, and a separately stored endpoint reference of **85.583454 g/L**. The **80 g/L** demo target is set explicitly in `replay_data.SPECTRAL_TARGET`. The target gap shows distance from this threshold. Forecast error is calculated against the simulated endpoint after it is released.

The illustrative generator `ethanol-template-interpolation-v1` uses NumPy seed **7291**. It sorts the 116 Model 1 training spectra by their ethanol assay, divides them into eight groups, and averages each group's assay concentration and spectrum. Each timestamp's latent smooth trajectory runs from the lowest to the highest group mean, about 23.378 to 86.116 g/L. The generator interpolates each of the 235 derivative-absorbance channels between neighbouring forward templates and adds independent seeded channel noise scaled to 0.5% of that channel's training standard deviation. The final assay adds separate Gaussian noise with a 0.4 g/L standard deviation to latent terminal ethanol. The generator uses the source feature names, order and representation, with no inversion or use of fitted PLS coefficients to generate its spectra.

At simulated hour 30, the following stored inputs reproduce the saved result.

| Timestamp | First four saved derivative channel values in source order | PLS ethanol (g/L) | Direct simulated ethanol (g/L) |
| --- | --- | ---: | ---: |
| Hour 28 | 0.002663478, 0.003486855, 0.004291093, 0.004959805 | 78.558455 | 78.476808 |
| Hour 30 | 0.002550852, 0.003392541, 0.004274780, 0.005059106 | 81.070359 | 81.009289 |

The PLS path feeds Ridge **81.070359 g/L**, **1.255952 g/L/h**, and **6 h** remaining. The restored Ridge predicts **83.494674 g/L**, saved as the hour-30 forecast. Its distance from the 80 g/L demo target is **+3.494674 g/L**. The direct comparison uses **81.009289 g/L**, **1.266241 g/L/h**, and **6 h** remaining. It uses the same fit and forecasts at the same 34 issue times.

| Path, one example batch | Hour-30 forecast (g/L) | Hour-30 signed error (g/L) | Hour-35 forecast (g/L) | Hour-35 signed error (g/L) |
| --- | ---: | ---: | ---: | ---: |
| Simulated spectra → saved PLS → saved Ridge | 83.494674 | −2.088779 | 66.617888 | −18.965565 |
| Direct simulated ethanol → same saved Ridge | 83.449373 | −2.134081 | 67.080996 | −18.502458 |

The hour-30 PLS current estimate differs from the simulator's latent ethanol by **+0.061070 g/L**. The two discharge forecasts differ by only **0.045302 g/L** at hour 30 and **0.463108 g/L** at hour 35. Most of the late example error persists even with direct simulator readings. The example's late concentrations and slopes differ from the typical 36-hour histories used to train Ridge. This paired check isolates the input paths for this trajectory. The single example was excluded from all fitting and tuning, and it supplies no evidence of real spectral realism or factory discharge accuracy. Those require paired process spectra and assays over independent complete batches.

## Saved experiment results

Model 1 uses snapshot `f0e482970f5c538ca87bd8ae8c35017a5f43d08b0ff367437b5f131940eaa9dd`, 235 channels in source order, and the previous seed-42 split of 116/25/25. The ethanol artifact stores the equivalent wavelength-space equation for the scaled 10-component PLS fit. The glucose artifact stores feature means and scales, support spectra, signed weights, intercept and gamma for the saved RBF SVR (C = 1000, gamma ≈ 0.00425531915, epsilon = 0.01 g/L). Both restored equations were checked against the original fitted pipelines across all 166 source rows before publication. Saved selected-experiment validation and held-out predictions support the UI plots and metrics. The default PLS/SVR searches produced 55 candidate rows per target, with held-out comparison metrics for the method winners. The prior reports remain available for past interactive variants.

| Model 1 target | Validation MAE / RMSE (g/L) | Held-out MAE / RMSE (g/L) |
| --- | --- | --- |
| Ethanol PLS | 1.140681 / 1.469649 | 1.062083 / 1.489760 |
| Glucose RBF SVR | 3.173749 / 4.796200 | 2.908846 / 3.561681 |

The restored Ridge uses features ordered as latest ethanol, two-hour ethanol slope, and time remaining to scheduled discharge. Its standardized coefficients are **45.702688, 4.014486, 40.863508**, with intercept **120.704731 g/L** and selected alpha **10**. The training means are **67.666590, 3.297481, 17.5** and scales are **34.556420, 1.164572, 9.810708**. The scaler was fitted on 8,160 training windows from 240 batches. Validation and held-out each use 2,720 windows from 80 separate batches. The operators' showcases and the synthetic spectral batch are outside these splits.

### Model 2 held-out synthetic performance

The following are saved comparisons at matched issue times and endpoints. Each method uses 80 synthetic batches per lead. Ridge beats extrapolation by MAE at 12 and 6 hours. The two-hour baseline does better at the shortest lead. These scores establish performance on the seeded synthetic test distribution.

| Lead (h) | Ridge MAE (g/L) | Ridge RMSE (g/L) | Trend MAE (g/L) | Trend RMSE (g/L) |
| ---: | ---: | ---: | ---: | ---: |
| 12 | 5.634 | 6.926 | 9.603 | 11.696 |
| 6 | 4.245 | 5.367 | 4.857 | 5.736 |
| 2 | 6.732 | 8.252 | 2.400 | 2.953 |

## Turso publication

Before this change, Turso stored source data and alignment only. Reused physical tables are `dataset_versions`, `spectral_inputs`, `reference_outputs`, and `test_alignment`. Both the NIR snapshot and the earlier chemotools snapshot remain present. The following physical result tables are new.

| Table | Rows in the release | Relationship and payload |
| --- | ---: | --- |
| `model_runs` | 3 | Versioned ethanol PLS, glucose SVR, and Ridge experiments. The calibrations reference the existing source snapshot. |
| `model_artifacts` | 3 | One `equations-json-v1` artifact per run, with ordered features and fitted inference state. |
| `model_metrics` | 129 | Per-run selected, candidate and comparison metrics with split, method, evaluation slice and counts. |
| `model_predictions` | 5,540 | 100 Model 1 validation/test rows and 5,440 Model 2 held-out method/window rows, with prediction and paired reference. |
| `replay_batches` | 5 | Three direct showcases, one public replay and one generated spectral batch, with source and linked model runs. |
| `replay_observations` | 1,358 | Per-batch minute and release time, saved ethanol, and optional process channels. Public spectral keys reference `spectral_inputs`. Generated spectra are stored as ordered JSON arrays beside the corresponding observations. |
| `replay_forecasts` | 170 | References a batch and the saved Ridge run. Stores issue, lead, features, availability and prediction across 102 showcase issues and 68 generated-scenario path issues. |

Publication is atomic. Backfill checks restored equations against original pipelines, builds observations and forecasts, inserts related rows and checks the counts within a single transaction before exposing published runs. Primary and composite keys prevent duplicates. A completed release is reused on a second invocation. Streamlit uses saved records and recomputes parity through the same inference and feature functions on cache load. The playback operation applies its time filter in memory and has no write path.

**Version keys.** Release `replay-results-v1`, estimator environment scikit-learn **1.9.1**. Keys are SHA-256 identifiers over release, verified source snapshot, estimator version and run or replay name. Prefixes below identify the rows in this release.

| Run or replay | Key prefix |
| --- | --- |
| Model 1 ethanol PLS | `f5e68495f89e` |
| Model 1 glucose SVR | `e13590d90ad2` |
| Model 2 Ridge | `b81c318307dc` |
| F-0607 | `e0ae05f8a7ab` |
| F-0608 | `26f69bba4abc` |
| F-0609 | `2b9b907cccae` |
| Public NIR replay | `f31e861a0a47` |
| SIM-NIR-01 | `c93fa6ff2226` |

Run these commands from the project root using the configured credentials. Credentials stay in the existing local configuration.

```powershell
.\.venv\Scripts\python.exe backfill_results.py migrate
.\.venv\Scripts\python.exe backfill_results.py backfill
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address=127.0.0.1 --server.port=8505
```

## Changed files and ownership

The project keeps its existing flat Python layout.

| Files changed | Responsibility |
| --- | --- |
| `app.py`, `batch_monitor.py` | Streamlit pages, rendering, and session-state clock. |
| `replay_data.py` | Scenario identities, timestamped inputs and deterministic forward spectrum simulation. Existing `example_data.py` supplies the untouched direct showcases. |
| `model_1a.py`, `fitted_state.py` | Model 1 fitting and evaluation exports, and portable inference for PLS, SVR and Ridge. |
| `model_2.py` | Shared causal feature builder and fitting/evaluation. Forecasts carry their input feature values for persistence and replay checks. |
| `turso_database.py`, `results_store.py` | Turso transport and migration discovery, result versioning, publication, reads, and inference parity. Existing `spectral_store.py` still owns the source snapshot imports. |
| `migrations/002_model_results.sql`, `backfill_results.py` | Idempotent result schema and explicit backfill. |
| `README.md`, this report | Commands, code ownership, relationships, results and limitations. |

## Verification

- Applied the Turso migration and backfill with the configured credentials. A second backfill reported no rows written and the same counts in all seven tables. Inspected the physical table names and confirmed the historical dataset snapshots remained present.
- Read every replay and both selected calibration experiments back from Turso. Restored PLS estimates matched the saved public/generated observations and the restored Ridge reproduced the saved monitor features and forecasts within 1 × 10⁻⁹ g/L numeric tolerance. Replacing later observations with substantially different values did not change the hour-30 features. Final references are stored separately from inference rows.
- Recomputed the held-out metrics for the three published Model 2 lead slices and checked the baseline and restored Ridge outputs from saved input features. Checked the synthetic spectral checkpoint against its saved 235-channel spectra, the PLS equation, and the three Ridge inputs.
- Regenerated the 1,081 synthetic spectra from the documented source and seed. All stored spectrum vectors and timestamps matched exactly. The largest direct-ethanol difference after Turso storage was 7.11 × 10⁻¹⁵ g/L and the endpoint matched exactly.
- Repeated both Model 1 experiment selections with fitting and tuning functions patched to raise if called. The saved views rendered successfully. Compared the plots' underlying datasets with the Turso predictions for both Model 1 targets and all three Model 2 leads. Checked the displayed Ridge coefficients and metrics against the published state and verified that missing results produce a backfill recovery message.
- Exercised all three direct scenarios, the public NIR replay and the synthetic spectral batch in Streamlit AppTest. Verified resets, the first valid forecast, the hour-30 checkpoint, the hour-36 reference release, and backward scrubbing. The app health endpoint returned `ok`.
- In headless Chrome, verified Play, Pause, Resume, manual steps, batch and source resets, automatic stop at both spectral endpoints, the hour-30 checkpoint, and reference removal after scrubbing backward and the view settling. Public NIR playback took 7.09 seconds to its final 5 h 30 min state. Full synthetic spectral playback took 36.63 seconds to its final hour-36 state. Repeated selection on the registered Model Training & Validation route also passed.
- Factory accuracy could not be measured because compatible complete-batch histories with verified schedules and independent discharge assays were unavailable.
