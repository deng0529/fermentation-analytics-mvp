# SVR tuning comparison

Local app: [http://localhost:8501](http://localhost:8501). Run SVR fits the selected settings and shows the validation-ranked tuning table. The selected and validation-winning configurations have a separate held-out test section.

## Estimator, preprocessing, and candidates

- Direct estimator `sklearn.svm._classes.SVR`, imported as `from sklearn.svm import SVR`. Installed package `scikit-learn 1.9.1`. The estimator uses libsvm.
- Turso NIR snapshot `f0e482970f5c538ca87bd8ae8c35017a5f43d08b0ff367437b5f131940eaa9dd`. Both targets used all 235 source-order first-derivative channels and the same seed-42 split of 116 training, 25 validation and 25 held-out test rows.
- StandardScaler centers and scales the feature columns using the training rows only. All candidates and the manual fit reuse it. Targets remain in g/L. The previous baseline is RBF, C = 10, gamma = 0.05 and epsilon = 0.1 g/L.
- Stage 1 uses RBF with epsilon 0.1 g/L, C = [0.1, 1, 10, 100, 1000], and gamma = [0.1×, 1×, 10×] the numeric training gamma scale. Stage 2 adds epsilon [0.01, 0.5, 1.0] g/L for the three stage-1 configurations with lowest validation RMSE.
- The baseline and manual configuration are scored after both stages. Equivalent effective settings share one row and retain their markers. The lowest validation RMSE also minimizes validation MSE. The selected and winning test evaluations happen after ranking.

## Actual validation results

| Target | Configuration | C | Effective gamma | Epsilon (g/L) | Validation MSE ((g/L)²) | Validation RMSE (g/L) | Samples |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Ethanol | Previous baseline | 10 | 0.05 | 0.1 | 62.882709 | 7.929862 | 25 |
| Ethanol | Validation winner | 1000 | 0.000425531914894 | 0.5 | 1.719478 | 1.311289 | 25 |
| Ethanol | Changed manual run (linear) | 1 | — | 0.5 | 2.995520 | 1.730757 | 25 |
| Glucose | Previous baseline | 10 | 0.05 | 0.1 | 73.102630 | 8.550008 | 25 |
| Glucose | Validation winner | 1000 | 0.00425531914894 | 0.01 | 23.003537 | 4.796200 | 25 |
| Glucose | Changed manual run (linear) | 1 | — | 0.5 | 60.775212 | 7.795846 | 25 |

Numeric gamma scale was 0.00425531914894. The default selection produced 25 unique rows (24 tuning candidates plus the baseline). The changed manual run used linear SVR, C = 1 and epsilon = 0.5 g/L, adding one distinct row. All fits succeeded.

## Held-out test results

| Target | Configuration | Samples | MAE (g/L) | RMSE (g/L) | Signed bias (g/L) |
| --- | --- | ---: | ---: | ---: | ---: |
| Ethanol | Selected baseline | 25 | 6.097572 | 7.774717 | -0.810001 |
| Ethanol | Validation winner | 25 | 1.158265 | 1.534007 | +0.143226 |
| Ethanol | Changed manual run (linear) | 25 | 1.131895 | 1.605592 | +0.155493 |
| Glucose | Selected baseline | 25 | 4.946241 | 6.288532 | +1.586519 |
| Glucose | Validation winner | 25 | 2.908846 | 3.561681 | +0.753867 |
| Glucose | Changed manual run (linear) | 25 | 4.842100 | 5.879651 | +2.260596 |

## Verification

- Ran the default RBF settings and then linear SVR with C = 1 and epsilon = 0.5 g/L for each NIR target through the running local Streamlit app. The selected result followed the controls. The complete tuning table appeared below the single Run SVR button on every run, with 25 rows when the selection matched the baseline and 26 when it differed. Verified the separate held-out test section and the one existing selected-run scatter plot.
- Switched targets and confirmed each retained its own results. Verified that NIR PLS, the joint PLS vs SVR summary, and chemotools PLS cross-validation still worked.
- Instrumented the scaler to confirm it fitted once using all 235 columns from the same 116 training rows. Verified the manual changes left both tuning stages unchanged, equivalent gamma settings retained their markers in one row, and test evaluation used only the 25 designated test rows. In a controlled check, changing only test references affected test scores without changing any validation result or rank. A controlled fit failure appeared at the bottom with a failure status.
- Python compilation passed and the main Streamlit server responded on localhost:8501.

## Files changed

- `app.py` connects the existing Run SVR button to tuning and shows the comparison, selected run, and held-out check.
- `nir_calibration.py` fits the shared training scaler, builds and ranks the candidates, and evaluates the selected fit and validation winner on the test split.
- `SVR_COMPARISON_REPORT.md` records the results and verification.
