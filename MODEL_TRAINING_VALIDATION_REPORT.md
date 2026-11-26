# Model Training & Validation

The app is available at [localhost:8501](http://localhost:8501). Training loads the selected dataset directly from Turso. Preprocessing & Feature Selection retains its selectors and explanatory content.

## Data and split

The four runs used the chemometrics::NIR Turso snapshot `f0e482970f5c538ca87bd8ae8c35017a5f43d08b0ff367437b5f131940eaa9dd`. Each target used all 235 published first-derivative spectral channels in source order and 166 paired values from its own lab reference column, `Ethanol` or `Glucose`.

The existing seed-42 split assigned the same 116 training, 25 validation, and 25 test samples to both targets and methods. PLS and SVR fitted on training rows. SVR used a single fitted `StandardScaler` for both evaluation splits. Compare settings using validation MAE and use test metrics as the held-out performance check.

## Run settings and actual metrics

PLS used two components with training-only PLS scaling. The centered training matrix had rank 115, which is the upper limit in the control. SVR reused the app’s RBF defaults with C = 10, epsilon = 0.1, and gamma = 0.05. The runs used scikit-learn 1.9.1.

| Target | Method | Split | Samples | MAE (g/L) | RMSE (g/L) | Signed bias (g/L) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Ethanol | PLS | Validation | 25 | 5.267 | 7.256 | −0.660 |
| Ethanol | PLS | Held-out test | 25 | 4.793 | 6.494 | −0.848 |
| Ethanol | SVR | Validation | 25 | 5.801 | 7.930 | +0.496 |
| Ethanol | SVR | Held-out test | 25 | 6.098 | 7.775 | −0.810 |
| Glucose | PLS | Validation | 25 | 8.326 | 10.065 | +0.623 |
| Glucose | PLS | Held-out test | 25 | 8.922 | 10.275 | +1.776 |
| Glucose | SVR | Validation | 25 | 5.736 | 8.550 | −1.472 |
| Glucose | SVR | Held-out test | 25 | 4.946 | 6.289 | +1.587 |

Signed bias is mean(predicted − measured). With these settings, PLS had the lower validation MAE for ethanol and SVR had the lower validation MAE for glucose. Runs and their settings are retained in the Streamlit session for the exact dataset version, target, method, and split.

## Verification

- Ran PLS and SVR for both NIR targets through the live Streamlit agent API using the real Turso snapshot. Checked the three selector options, reference labels, evaluation metrics, chart outputs, and that comparison appeared after both methods had run for the selected target.
- Independently checked the full source-index assignments, source-order features, selected reference values, and metric calculations. Instrumented the PLS fit and SVR scaler to verify they each received only the training rows. Checked rejection of a PLS component count above the matrix rank.
- Verified target switching preserved the correct results, edited settings left the previous run’s settings visible, and the confirmation button was absent from preprocessing. Verified that chemotools shows 21 training pairs, 1,047 channels, planned cross-validation, and a separate test run of 1,629 spectra and 34 HPLC records without an executable training action.

The metric verification covers the requested default PLS and RBF SVR runs. Custom hyperparameter sweeps, including linear SVR metrics, were outside this check. Chemotools training is planned for the next iteration.

## Files changed

- `app.py` adds the live training workflow and removes preprocessing confirmation.
- `nir_calibration.py` shares the existing split and implements fitting and evaluation.
- `spectral_store.py` returns the identifier of the exact Turso snapshot used for training.
- `requirements.txt` declares the scikit-learn dependency.
- `README.md` documents the current workflow.
- `MODEL_TRAINING_VALIDATION_REPORT.md` records the settings, metrics, and checks.
