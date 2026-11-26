# Fitted Model 1A displays

The app is running at [http://localhost:8501](http://localhost:8501). Model Training & Validation starts with **Select the data source** and offers NIR ethanol and glucose. Selecting a target reconstructs its fixed fit and caches the result by target and snapshot.

Both models use Turso NIR snapshot `f0e482970f5c538ca87bd8ae8c35017a5f43d08b0ff367437b5f131940eaa9dd`, all 235 channels in source order, and the original seed-42 split of 116 training, 25 validation, and 25 held-out rows. The app reconstructs the verified settings with scikit-learn 1.9.1.

## Ethanol · 10-component PLS

Ten components had the lowest validation MAE in the earlier PLS sweep. On the same 25 held-out rows, this fit had lower MAE and RMSE than tuned SVR (1.158265 and 1.534007 g/L), so it is the ethanol demo model.

The displayed rule is **predicted ethanol = b + Σⱼ kⱼxⱼ**, where xⱼ is the published first-derivative absorbance value at wavelength j. The ten learned components combine the 235 inputs. In the installed `PLSRegression` implementation, `coef_` already incorporates the fit’s scaling. The effective intercept in the original coordinates is the model prediction at the zero vector, **24.521225000012237 g/L**. The app displays and exports all 235 coefficients with the exact source labels and wavelength values.

Maximum absolute difference between the displayed equation and estimator over the 25 held-out rows was **8.53 × 10⁻¹⁴ g/L**. Reconstructing from the CSV coefficients produced the same maximum difference.

## Glucose · tuned RBF SVR

Tuned SVR had lower validation and held-out errors than PLS in the earlier glucose comparison. The reconstructed settings are RBF, C = 1000, gamma = 0.00425531914893617, and epsilon = 0.01 g/L.

The displayed rule is **predicted glucose = b + Σᵢ αᵢ exp(−gamma × ‖z − sᵢ‖²)**. The rule forms z by subtracting the training-fitted feature means and dividing by the training-fitted scales. Each sᵢ is a support spectrum in those scaled coordinates and αᵢ is its signed dual coefficient. The intercept is **6.049900251134118 g/L**, and the fitted model has **115 support vectors**. The app displays and exports the vectors and weights, their original source row positions, and the 235 ordered scaler means and scales.

Maximum absolute difference from the fitted estimator was **4.23 × 10⁻¹³ g/L**. Using the CSV parameters and the gamma precision displayed in the app, the maximum difference was **2.18 × 10⁻¹¹ g/L**.

## Reproduced scores

| Target and model | Split | Samples | MAE (g/L) | RMSE (g/L) |
| --- | --- | ---: | ---: | ---: |
| Ethanol PLS | Validation | 25 | 1.140681 | 1.469649 |
| Ethanol PLS | Held-out test | 25 | 1.062083 | 1.489760 |
| Glucose SVR | Validation | 25 | 3.173749 | 4.796200 |
| Glucose SVR | Held-out test | 25 | 2.908846 | 3.561681 |

Both test scores match the previous report to six decimal places. The scatter plots use the 25 held-out predictions, measured concentration on x, predicted concentration on y, and a dashed y = x reference. The tooltip includes the source row position and label.

## Active sources and verification

- Exercised all four pages on a running local Streamlit verification instance. The default training view had an empty selector and no model results. Switching ethanol → glucose → ethanol switched the fitted settings, parameter tables, metrics, and single plot together. Verified the CSV download controls and tested the serialized CSV contents independently.
- The verification instance rejected any data source other than NIR and any call to the tuning search. It reconstructed each model once and reused the cached ethanol fit on revisit. The active dataset selectors and inventory showed no Model 1B entries.
- Found no matching enabled Windows scheduled task, Python import process, or local Codex automation definition. The default import command requests only NIR. A read-only Turso count confirmed that the historical dataset retains 1,650 spectra, 55 references, and 34 alignment records. Historical reports remain available.
- Verified the main server health on localhost:8501. The scheduler checks covered this workstation.

## Files changed

- `app.py` removes Model 1B from the active pages and displays the Model 1A rules, downloads, metrics, and held-out plots.
- `model_1a.py` reconstructs the fits, exports their parameters, and verifies their equations.
- `example_data.py` removes the retired dataset from the app’s example source inventory.
- `spectral_store.py` defaults the import command to NIR. Historical datasets still require explicit selection.
- `README.md` describes the active workflow.
- `MODEL_1A_DISPLAY_REPORT.md` records the equations, scores, and checks.
