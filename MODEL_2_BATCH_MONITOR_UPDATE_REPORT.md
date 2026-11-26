# Ethanol-only Batch Monitor and Model 2 update

26 November 2026 · [Open the local Batch Monitor](http://127.0.0.1:8504/batch-monitor)

## Playback and forecast timing

Play advances the current position by one simulated hour on each one-second Streamlit fragment tick. The validation section sits outside that fragment. Pause retains the current position. Restart, Previous hour, Next hour, slider changes, and source or batch changes pause playback. Restart and source or batch changes reset the clock to zero. Each tick renders the latest visible state; playback does not change model issue times.

In a local headless Chrome run, the synthetic replay took **36.94 seconds** from Play to the rendered hour-36 endpoint. The browser observed every state from hour 0 through hour 36 in order. The spectral replay took **7.47 seconds** in the browser and stopped at **5 h 30 min**, including its final half-hour step. These wall-clock measurements include browser interaction and rendering. Both endpoints automatically stopped playback.

In the three synthetic scenarios, a shared Ridge fit issues 34 forecasts at hours 2–35, each for hour 36. The hour-30 issue is marked as the six-hour checkpoint. The final simulated ethanol reference appears at hour 36 and the forecast card keeps the hour-35 issue. Scrubbing backwards hides future forecasts, readings, and references.

| Scenario | Hour-30 forecast (g/L) | Hour-35 forecast (g/L) | Hour-36 simulated reference (g/L) |
| --- | ---: | ---: | ---: |
| F-0607 · Shortfall | 127.3 | 115.2 | 120.4 |
| F-0608 · On target | 142.5 | 130.9 | 133.1 |
| F-0609 · Recovery | 141.2 | 129.8 | 131.3 |

The names identify the original operator scenarios. Warnings use the computed forecast against the 130 g/L target. F-0609 is above target at the checkpoint and slightly below it at its last pre-discharge issue.

## Spectral clock, ethanol trend, and forecast availability

The selected Turso `chemometrics::NIR` snapshot is `f0e482970f5c538ca87bd8ae8c35017a5f43d08b0ff367437b5f131940eaa9dd`. Its **166 spectra** replay in source positions 1 through 166, with the first row `R1 zaM 1` at **minute 0** and the last row `VM3_7z` at **minute 330**. The assigned interval is **two minutes**. There are 165 intervals, so the final timestamp is `(166 − 1) × 2 = 330` minutes, or **5 h 30 min**. The previous `batch_monitor.py` used a literal `SPECTRAL_DISCHARGE = 330` as both the replay bound and the displayed discharge time. The updated view derives the bound from the loaded row count and separately shows **Scheduled discharge · Unknown**.

The trend and recent readings use the existing **10-component ethanol PLS** fit with its original training split and estimator scaling. The inference path validates all 235 first-derivative spectral channel names and their order before predicting ethanol in g/L. All 166 timeline values matched direct Model 1 predictions on the same rows exactly in the verification run. For example, the first and last values were **41.280347** and **88.067481 g/L**. Playback displays the estimates as calculated. The UI explains that a calibration sequence can fluctuate because source order supplies no verified fermentation trajectory.

Operational discharge forecasting is unavailable for this sequence. A user can enable **Demonstration only** and set a simulated discharge time, initially 360 minutes. This is independent of the replay end and leaves the real discharge schedule labelled Unknown. The shared model emits pre-target hourly demonstration forecasts where the two-hour inputs are available, with warnings disabled. For example, at simulated hour 2, its inputs are 66.733145 g/L latest ethanol, 12.726399 g/L/h two-hour slope, and 4 h until assumed discharge. The model predicts **95.743219 g/L**. Training uses hourly, contiguous synthetic histories from individual 36-hour batches. The spectral rows instead have artificial two-minute spacing and can produce substantially different slopes. There is no independent spectral discharge label, so demonstration predictions carry no validated discharge accuracy claim.

## Model 2 fit

One forecast window supplies (X) with three ordered features. The output (y) is one final ethanol reference in g/L for each forecast window, repeated across the windows of the same batch.

| Split | Distinct batches | Forecast windows | X shape | y shape |
| --- | ---: | ---: | --- | --- |
| Training | 240 | 8,160 | 8,160 × 3 | (8,160,) |
| Validation | 80 | 2,720 | 2,720 × 3 | (2,720,) |
| Held-out test | 80 | 2,720 | 2,720 × 3 | (2,720,) |

`model_2.py` generates ethanol histories and separate noisy hour-36 endpoint references with seed 2601. Each batch stays in one split and the three operator scenarios are excluded. Removing the other concentration's generator draws changes the seeded ethanol realisations relative to the earlier release. The Ridge and trend results below share the same new held-out data. For every forecast issue, the same time-aware feature function checks both ends of the two-hour window and uses observations released by the issue time. The endpoint reference serves as the supervised label.

The fitted Ridge objective minimises the sum of squared prediction errors plus `alpha × (w₁² + w₂² + w₃²)` using standardized features. The intercept is fitted without a penalty. The prediction is `120.704730837 + w₁z₁ + w₂z₂ + w₃z₃` g/L, where `zⱼ = (xⱼ − training meanⱼ) / training scaleⱼ`.

| Feature | Training mean | Training scale | Standardized coefficient |
| --- | ---: | ---: | ---: |
| Latest ethanol (g/L) | 67.66659034 | 34.55641958 | 45.70268765 |
| Two-hour ethanol slope (g/L/h) | 3.29748148 | 1.16457226 | 4.01448620 |
| Hours remaining to discharge | 17.50000000 | 9.81070844 | 40.86350802 |

The StandardScaler and estimator fit only on training windows. Candidate alphas **0.01, 0.1, 1, 10, 100** produced validation MAE values of **10.708705, 10.708443, 10.705839, 10.683716, and 10.821817 g/L** respectively. The selected alpha was **10**. The app uses a new cached fitting function keyed by `ethanol-only-v2` and the exact ordered feature names, and verifies that the fit has that schema.

## Synthetic held-out results

Trend extrapolation adds the latest ethanol estimate to the two-hour slope multiplied by hours remaining. Both methods use the same 80 held-out batches at each issue time. MAE averages absolute errors. MSE averages squared errors. RMSE is the square root of MSE and uses the same units as ethanol. Bias is prediction minus reference. Warning denominators are the 36 actual shortfalls and 44 actual results at or above 130 g/L.

| Lead (h) | Method | n | MAE (g/L) | MSE ((g/L)²) | RMSE (g/L) | Bias (g/L) | Missed shortfalls | False warnings |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 12 | Ridge | 80 | 5.634 | 47.975 | 6.926 | +0.794 | 1/36 | 4/44 |
| 12 | Trend | 80 | 9.603 | 136.795 | 11.696 | +2.398 | 4/36 | 6/44 |
| 6 | Ridge | 80 | 4.245 | 28.801 | 5.367 | +0.681 | 1/36 | 2/44 |
| 6 | Trend | 80 | 4.857 | 32.897 | 5.736 | +1.229 | 2/36 | 4/44 |
| 2 | Ridge | 80 | 6.732 | 68.101 | 8.252 | −0.452 | 3/36 | 3/44 |
| 2 | Trend | 80 | 2.400 | 8.723 | 2.953 | +0.413 | 3/36 | 3/44 |

Ridge had lower MAE at 12 and 6 hours. The trend baseline had lower MAE at 2 hours. The shared Model 2 details section shows these results with a predicted-versus-reference scatter plot and equality diagonal, defaulted to the six-hour lead. Accuracy was verified against synthetic held-out labels only.

## Local verification

- Headless Chrome exercised Play, Pause, Resume, Restart, manual navigation during playback, both automatic endpoints, batch and source resets during playback, and backward scrubbing from the synthetic endpoint. The spectral test confirmed the exact final timestamp, the last estimate, the Unknown schedule, and the optional demonstration path.
- Streamlit AppTest exercised all three synthetic selections, the startup and first forecast, the checkpoint, the final reference, and backward slider navigation. It compared displayed split counts, coefficients, and metrics with the computed values, exercised all three validation leads, and checked that the Batch Monitor exposed no glucose data or explanations.
- Numeric checks reproduced the fitted equation on held-out windows, verified MSE against squared RMSE, checked that changing future readings leaves earlier forecasts unchanged, and confirmed the exact ethanol feature names and order. All spectral estimates and timestamps matched the loaded sequence. Reversed source channels were rejected. The independent Model 1 reconstruction retained its previous held-out results for both ethanol PLS and glucose SVR.
- Repeated loads reused the cached three-feature fit. A load using the prior five-feature schema was rejected. The local app health endpoint returned `ok` after verification.
- No verified real fermentation timing, operational discharge schedule, or independent discharge assay was available for spectral evaluation. Playback timings are measurements from this workstation.

## Changed files

- `batch_monitor.py` implements fragment playback, ethanol-only operator views, separate spectral timing, demonstration controls, and expanded validation details.
- `model_2.py` implements the versioned three-feature schema, ethanol-only synthetic fitting, actual split dimensions, MSE, and warning denominators.
- `README.md` describes playback and the updated replay modes.
- `MODEL_2_BATCH_MONITOR_UPDATE_REPORT.md` records the implementation and checks.
