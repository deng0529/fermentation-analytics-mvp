# Automatic model comparison and final test

Local app: [http://localhost:8501](http://localhost:8501). Select an experiment to run validation and view both winners' final test scores in one table.

## Data, selection, and fitting

- NIR Turso snapshot `f0e482970f5c538ca87bd8ae8c35017a5f43d08b0ff367437b5f131940eaa9dd`. Both targets use all 235 first-derivative channels and the same seed-42 assignments: 116 training, 25 validation and 25 held-out test samples. The final models fit on the original 116 training rows.
- Chemotools Turso snapshot `68520f938e78e2f74ca64b424afdcc9d7eabf04fbe8c299a55f3006c5f12de89`. All 1,047 features and the same 21 calibration pairs. Both methods use shuffled five-fold cross-validation with seed 42 and pooled predictions. Train/validation sizes were 16/5, 17/4, 17/4, 17/4, 17/4. Final models fit on all 21 pairs.
- PLS candidates are components 1–30 for NIR and 1–10 for chemotools, capped by centered training rank. The lowest validation MAE wins, with smaller component counts breaking exact ties.
- The existing SVR search uses RBF, C = [0.1, 1, 10, 100, 1000], epsilon = 0.1 g/L and gamma = [0.1×, 1×, 10×] training gamma scale. For the three lowest-RMSE first-stage candidates it also tries epsilon 0.01, 0.5 and 1.0 g/L. The prior RBF baseline (C 10, gamma 0.05 and epsilon 0.1 g/L) is included. Lowest validation RMSE wins. StandardScaler fits within each training split or fold. Gamma scale uses 1 / (feature count × scaled-training population variance), with the winning relative rule recomputed on all 21 pairs for the chemotools final fit. Targets stay in g/L.
- Direct estimator classes: `sklearn.cross_decomposition._pls.PLSRegression` with `scale=True` and `sklearn.svm._classes.SVR` using libsvm, both in scikit-learn 1.9.1. NumPy 2.5.5, pandas 3.1.1, and Streamlit 1.67.0 were installed for verification.

## Six selected fits

Errors are in g/L. Signed bias is mean(predicted − measured). Settings were selected before final test scoring.

| Experiment | Method | Winning settings | Validation n | Validation MAE | Validation RMSE | Test n | Test MAE | Test RMSE | Test bias |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| NIR ethanol | PLS | 10 components | 25 | 1.140681 | 1.469649 | 25 | 1.062083 | 1.489760 | +0.015049 |
| NIR ethanol | SVR | RBF, C 1000, 0.1× scale, final gamma 0.000425531914894, epsilon 0.5 g/L | 25 | 1.106129 | 1.311289 | 25 | 1.158265 | 1.534007 | +0.143226 |
| NIR glucose | PLS | 11 components | 25 | 4.797815 | 6.349095 | 25 | 3.736058 | 4.627984 | +0.709963 |
| NIR glucose | SVR | RBF, C 1000, 1× scale, final gamma 0.00425531914894, epsilon 0.01 g/L | 25 | 3.173749 | 4.796200 | 25 | 2.908846 | 3.561681 | +0.753867 |
| chemotools glucose | PLS | 1 components | 21 | 7.291452 | 9.096959 | 34 | 196.297264 | 201.966416 | -196.297264 |
| chemotools glucose | SVR | RBF, C 100, 0.1× scale, final gamma 9.81354268891e-05, epsilon 0.01 g/L | 21 | 8.151310 | 10.260276 | 34 | 17.843357 | 19.094973 | -4.303130 |

NIR PLS reproduced the established winners: 10 components for ethanol and 11 for glucose.

## Approximate time alignment

Both chemotools winners predict all 1,629 fermentation spectra before the stored mapping selects predictions for the 34 matched HPLC records. Estimated spectrum time is acquisition position × 1.25 minutes from zero. The mapping picks the nearest estimated spectrum for each in-range recorded HPLC time, preferring the earlier spectrum on an exact tie. Scores use the original measured glucose from the HPLC table. Both winners use the same 34 matches.

The one-component chemotools PLS winner underpredicted glucose by 196.297 g/L on average over the 34 matched references. Its RMSE was 201.966 g/L. The chemotools SVR winner had a test RMSE of 19.095 g/L. Both methods selected settings from validation scores.

## Verification

- Exercised the running local Streamlit app through its agent API. The default view showed the selector with exactly three choices and no table. Instrumentation confirmed it ran neither a Turso load nor a model comparison.
- Selecting each experiment automatically produced one table. NIR showed 55 candidates per target, and chemotools showed 35. Both validation winners appeared first. Checked that test scores were present only for those winners and that the actual test sample counts were 25, 25, and 34 by experiment.
- Revisited all three experiments and verified identical winner rows. Instrumentation counted one comparison per experiment across the initial selections and revisits. Source data was checked again on each revisit.
- Checked that the SVR scaler fitted only on the expected training indexes, once per validation split or fold and once for the final fit. Verified that chemotools scored each of the 21 calibration pairs out of fold and used the original HPLC measurements at the stored matching indexes. All candidates completed on the tested snapshots.
- The main Streamlit server responded at localhost:8501. No requested check remains unverified.

## Files changed

- `app.py` provides the selector, input summary, cached comparison, and single results table.
- `nir_calibration.py` shares the PLS and SVR searches across hold-out and cross-validation workflows and evaluates their winners on the final test sets.
- `README.md` documents the selector-driven workflow.
- `MODEL_COMPARISON_AND_TEST_REPORT.md` records the settings, scores, and verification.
