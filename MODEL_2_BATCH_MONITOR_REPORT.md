# Model 2 Batch Monitor implementation

26 November 2026 · [Local Streamlit Batch Monitor](http://127.0.0.1:8503/batch-monitor)

The Batch Monitor now issues fitted Ridge forecasts from either synthetic concentration readings or actual Model 1 estimates. The three synthetic showcases retain their readings and simulated final references. The spectral demo uses real spectra with an assigned clock and keeps operational warnings disabled.

## Replay and data provenance

| Mode | Readings and clock | Forecasts and references |
| --- | --- | --- |
| Synthetic batch replay | F-0607, F-0608, and F-0609 start at hour 0. `example_data.py` provides the deterministic hourly ethanol, glucose, temperature and pH fixtures through hour 36. The concentration functions use the second value in each fixture tuple as a trajectory endpoint. | One Ridge forecast is issued each hour from 2 through 35 for discharge at hour 36. Hour 30 is the six-hour checkpoint. The separate third tuple value is the simulated ethanol sample and result released at hour 36. The old literal forecasts in the first tuple position are retained as historical fixture data and do not enter Model 2. |
| Model 1 spectral replay | All 166 rows of the retained Turso `chemometrics::NIR` calibration snapshot, in stored source row positions 1–166, from `R1 zaM 1` to `VM3_7z`. Row position (p) releases at simulated minute `2 × (p − 1)`, with the last row at minute 330. Spectral temperature and pH are unavailable. | Simulated discharge is at 5 h 30 min. Demonstration forecasts are issued at whole hours 2, 3, 4, and 5. The source has no verified complete-batch timeline or independent lab discharge reference. The demo supplies neither and disables operational warnings. |

The earlier [provenance audit](MODEL_2_DATA_PROVENANCE_REPORT.md) traces the original static 119.2 g/L display and documents the unavailable legacy archive. This implementation uses a new seeded statistical generator for training and evaluation. The showcases, their legacy forecasts, and their final lab values are outside fitting and alpha selection.

Both replay paths supply elapsed observation and release minutes, source provenance, and ethanol and glucose estimates to the same feature function. At a forecast issue, the function uses only released data and checks the age of the latest reading and the reading at the start of its two-hour window against the source cadence. The two slopes are changes between those readings divided by elapsed hours. Missing, stale, or non-finite inputs suppress the new forecast. Earlier valid forecasts retain their original issue times. Changing mode or selection resets the clock; scrubbing backwards rebuilds the visible readings, forecast history, and reference availability from that clock.

## Model 1 fits and a traced spectral forecast

Both the training page and replay reconstruct their fits via `model_1a.fit_calibration()`. They use snapshot `f0e482970f5c538ca87bd8ae8c35017a5f43d08b0ff367437b5f131940eaa9dd`, all 235 published first-derivative channels in their exact source order, and the same seed-42 split of 116 training, 25 validation, and 25 held-out rows.

- **Ethanol** uses 10-component PLS with the estimator's feature and reference scaling enabled.
- **Glucose** uses a training-fitted StandardScaler followed by RBF SVR with C = 1000, gamma = 0.00425531914893617, and epsilon = 0.01 g/L.

The replay releases only the spectral prefix through the clock to the prediction function, and the function checks the channel names and order against the fitted estimator. Lab references are used in reconstructing the fixed calibrations and excluded from prediction inputs and the Model 2 feature builder. The demonstration sequence includes calibration training rows and has simulated timing, so it does not support a spectral discharge accuracy estimate.

At simulated hour 2, 61 rows had been released. The feature builder used the calibrated values at the two-hour boundaries below.

| Source row | Simulated time | PLS ethanol (g/L) | SVR glucose (g/L) |
| --- | ---: | ---: | ---: |
| 1 · `R1 zaM 1` | 0 h | 41.280347 | 9.791162 |
| 61 · `VM2_m8` | 2 h | 66.733145 | 23.099670 |

In model order the inputs were **66.733145 g/L**, **23.099670 g/L**, **12.726399 g/L/h**, **6.654254 g/L/h**, and **3.5 h** remaining. The training scaler and fitted Ridge gave **89.566096 g/L**, displayed as **89.6 g/L** for simulated hour 5 h 30 min. The result illustrates the integration over compatible spectra, including values and changes that can differ from the synthetic training distribution.

## Model 2 fit and held-out synthetic results

`model_2.py` generates 400 synthetic hourly batches with NumPy seed 2601. Each has independently drawn trajectory parameters and noisy concentration observations. The simulated ethanol assay label is generated from the latent hour-36 ethanol with separate assay noise. The generator assigns entire batches to training, validation, or held-out test in a reproducible order. There are **240 training**, **80 validation**, and **80 held-out** batches, with 34 forecast rows per batch, or 8,160, 2,720, and 2,720 rows. Hour-36 concentrations and lab labels are excluded from inference features at every pre-discharge issue.

StandardScaler and Ridge are fitted together on training rows only. Validation MAE across all 34 issue hours selected **alpha 0.01** from **0.01, 0.1, 1, 10, and 100**. Their validation MAEs were 9.828366, 9.828368, 9.828434, 9.832448, and 10.130015 g/L. The fit is reconstructed locally and cached in Streamlit. The fitted intercept is **119.513499 g/L**. With training-scaled features, the coefficients in model order are **46.108899, −0.805273, 3.494770, 0.076470, and 42.232100**. The app shows the objective, equation, scaler means and scales, and validation plot in the collapsed Model 2 section.

The baseline extrapolates latest ethanol using its two-hour slope and remaining time. Each row below uses the same 80 held-out batch references and the same issue hour for both methods. Errors use g/L, bias is prediction minus reference, and alert counts use ethanol below 130 g/L.

| Lead (h) | Method | Samples | MAE | RMSE | Bias | Missed shortfalls | False warnings |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 12 | Ridge | 80 | 5.089 | 6.362 | +0.338 | 3 | 1 |
| 12 | Trend baseline | 80 | 9.510 | 11.626 | +1.362 | 5 | 2 |
| 6 | Ridge | 80 | 5.095 | 6.037 | −1.369 | 2 | 1 |
| 6 | Trend baseline | 80 | 4.577 | 5.923 | −0.816 | 3 | 0 |
| 2 | Ridge | 80 | 8.714 | 10.172 | −2.156 | 1 | 0 |
| 2 | Trend baseline | 80 | 2.136 | 2.798 | −0.115 | 1 | 0 |

Ridge had lower MAE at 12 hours. The trend baseline had lower MAE at 6 and 2 hours. A single Ridge fit was selected across all issue times. These results measure agreement with this generator's simulated references.

### Synthetic showcase results

The last pre-discharge forecast is issued at hour 35 and remains on screen at hour 36.

| Showcase | Hour-30 forecast (g/L) | Hour-30 target gap (g/L) | Retained hour-35 forecast (g/L) | Hour-36 reference (g/L) |
| --- | ---: | ---: | ---: | ---: |
| F-0607 · Shortfall | 128.6 | −1.4 | 116.7 | 120.4 |
| F-0608 · On target | 143.9 | +13.9 | 132.6 | 133.1 |
| F-0609 · Recovery | 142.7 | +12.7 | 131.4 | 131.3 |

The historical scenario names are preserved. F-0609 already forecasts above target at the six-hour checkpoint with the fitted Ridge. Its original static checkpoint forecast was below target.

## Verification and limits

- Started Streamlit locally and checked its health endpoint. Drove the registered Batch Monitor route through Streamlit's local agent API and verified the hour-30 display and chart sections. Streamlit AppTest also covered startup, previous and next hour, the first issue, hour 30, hour 36, and backward scrubbing for all three showcases. Verified 34 hourly forecasts per showcase, the computed warning at the checkpoint, the final reference, and retention of the hour-35 forecast.
- Switched from synthetic to spectral and back, checked clock resets and hidden prior results, exercised the full spectral path through simulated discharge, and injected a missing-snapshot error. Checked rejection of stale, delayed, missing, and non-finite feature inputs. Changing later synthetic readings did not affect earlier forecasts. A full spectral sequence and the released prefix gave the same hour-2 features within floating-point tolerance.
- Confirmed identical Model 1 held-out predictions between shared calibration inference and training-page reconstruction, and unchanged held-out Model 1 MAE and RMSE to six decimals. Verified that reversing the spectral columns raises an error. Exercised both calibration selections on the registered Model Training & Validation route through the local agent API.
- Refit Model 2 twice and compared held-out predictions and metrics. Checked the displayed metrics against the computed table and exercised the 12-, 6-, and 2-hour scatter views. The validation is synthetic. No independent measured discharge data were available for either a spectral end-to-end accuracy claim or plant validation.

## Files changed

- `app.py` routes Batch Monitor to the new view and caches the versioned NIR snapshot for five minutes.
- `batch_monitor.py` implements source selection, causal replay, operator displays, and Model 2 validation.
- `model_1a.py` shares fixed calibration fitting and validates inference channel order.
- `model_2.py` implements timestamped readings, shared features, the seeded generator, Ridge selection, and held-out comparison.
- `README.md` documents the two replays.
- `MODEL_2_BATCH_MONITOR_REPORT.md` records the implementation and verification.
