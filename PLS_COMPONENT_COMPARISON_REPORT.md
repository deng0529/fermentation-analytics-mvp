# PLS component comparison

Local app: [http://localhost:8501](http://localhost:8501). The **Run PLS** button fits the selected count and runs the full comparison. The comparison uses validation errors. The selected NIR run also reports the held-out test separately.

## Estimator and preprocessing

- Exact import in `nir_calibration.py`: `from sklearn.cross_decomposition import PLSRegression` (line 8).
- Direct estimator: `sklearn.cross_decomposition._pls.PLSRegression` at `nir_calibration.py:51`. Installed package: `scikit-learn 1.9.1`. The app instantiates the scikit-learn class directly.
- Estimator parameters held fixed: `scale=True`, `copy=True`, `max_iter=500` and `tol=1e-06`. Only `n_components` varies. PLS centers and scales X and y from the fit partition, with no additional preprocessing. All original channels are used in source order.
- NIR snapshot `f0e482970f5c538ca87bd8ae8c35017a5f43d08b0ff367437b5f131940eaa9dd`. All 235 published first-derivative channels. Shared seed-42 split of 116 training, 25 validation and 25 held-out test pairs. The test samples are evaluated only for the manually selected count, after the comparison.
- Chemotools snapshot `68520f938e78e2f74ca64b424afdcc9d7eabf04fbe8c299a55f3006c5f12de89`. All 1,047 training absorbance channels and 21 paired glucose references. Shuffled 5-fold `KFold` with seed 42. Fit/validation fold sizes: 16/5, 17/4, 17/4, 17/4, 17/4. Each candidate uses the same folds and one pooled set of 21 out-of-fold predictions. The fermentation test run is excluded.

MAE, RMSE, signed bias and SEP are in g/L. Signed bias is mean(predicted − measured). SEP is the sample standard deviation of those errors. Exact MAE ties select the smaller count.

## chemometrics::NIR — Ethanol

**Hold-out validation.** Candidates 1–30. Centered training rank: 115. The two-component baseline MAE was 5.266827 g/L. The lowest validation MAE was 1.140681 g/L at 10 components.

| Components | MAE (g/L) | RMSE (g/L) | Signed bias (g/L) | SEP (g/L) | Samples | Marker | Status |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 8.904994 | 11.725690 | -0.997910 | 11.924064 | 25 |  | OK |
| 2 | 5.266827 | 7.256382 | -0.659887 | 7.375326 | 25 | 2-component baseline | OK |
| 3 | 3.220417 | 4.128965 | -0.812812 | 4.131647 | 25 |  | OK |
| 4 | 2.109690 | 3.137198 | -0.235811 | 3.192831 | 25 |  | OK |
| 5 | 1.825618 | 2.782128 | -0.169392 | 2.834230 | 25 |  | OK |
| 6 | 1.645680 | 2.196946 | -0.186860 | 2.234124 | 25 |  | OK |
| 7 | 1.439136 | 1.888062 | +0.200211 | 1.916130 | 25 |  | OK |
| 8 | 1.417200 | 1.764356 | +0.269687 | 1.779578 | 25 |  | OK |
| 9 | 1.443156 | 1.749620 | +0.190504 | 1.775081 | 25 |  | OK |
| 10 | 1.140681 | 1.469649 | +0.231887 | 1.481165 | 25 | Lowest validation MAE | OK |
| 11 | 1.203278 | 1.585565 | +0.250409 | 1.597952 | 25 |  | OK |
| 12 | 1.233226 | 1.650857 | +0.296266 | 1.657545 | 25 |  | OK |
| 13 | 1.357265 | 1.696415 | +0.321745 | 1.699971 | 25 |  | OK |
| 14 | 1.352860 | 1.713152 | +0.335493 | 1.714623 | 25 |  | OK |
| 15 | 1.443965 | 1.808234 | +0.384363 | 1.803346 | 25 |  | OK |
| 16 | 1.456351 | 1.875575 | +0.381779 | 1.874174 | 25 |  | OK |
| 17 | 1.443264 | 1.834434 | +0.414255 | 1.823898 | 25 |  | OK |
| 18 | 1.480388 | 1.924735 | +0.508813 | 1.894541 | 25 |  | OK |
| 19 | 1.566972 | 2.023545 | +0.510568 | 1.998451 | 25 |  | OK |
| 20 | 1.556229 | 1.980069 | +0.488648 | 1.958394 | 25 |  | OK |
| 21 | 1.548298 | 1.907729 | +0.443369 | 1.893755 | 25 |  | OK |
| 22 | 1.571268 | 1.940942 | +0.451440 | 1.926639 | 25 |  | OK |
| 23 | 1.567390 | 1.941911 | +0.516707 | 1.910506 | 25 |  | OK |
| 24 | 1.623375 | 1.985985 | +0.556663 | 1.945685 | 25 |  | OK |
| 25 | 1.613545 | 1.977063 | +0.550134 | 1.938139 | 25 |  | OK |
| 26 | 1.619646 | 1.968085 | +0.515170 | 1.938631 | 25 |  | OK |
| 27 | 1.642403 | 1.985847 | +0.530955 | 1.953010 | 25 |  | OK |
| 28 | 1.663406 | 1.994261 | +0.533918 | 1.961082 | 25 |  | OK |
| 29 | 1.682361 | 2.031201 | +0.581048 | 1.986454 | 25 |  | OK |
| 30 | 1.716577 | 2.040974 | +0.574287 | 1.998898 | 25 |  | OK |

## chemometrics::NIR — Glucose

**Hold-out validation.** Candidates 1–30. Centered training rank: 115. The two-component baseline MAE was 8.325660 g/L. The lowest validation MAE was 4.797815 g/L at 11 components.

| Components | MAE (g/L) | RMSE (g/L) | Signed bias (g/L) | SEP (g/L) | Samples | Marker | Status |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 9.092959 | 11.905791 | +1.279368 | 12.080937 | 25 |  | OK |
| 2 | 8.325660 | 10.065107 | +0.623194 | 10.252947 | 25 | 2-component baseline | OK |
| 3 | 6.514099 | 7.831708 | +1.183046 | 7.901480 | 25 |  | OK |
| 4 | 5.709716 | 7.946679 | -0.204746 | 8.107853 | 25 |  | OK |
| 5 | 6.703729 | 9.508636 | -0.385515 | 9.696731 | 25 |  | OK |
| 6 | 5.984015 | 8.440404 | -0.107466 | 8.613753 | 25 |  | OK |
| 7 | 5.900938 | 8.008997 | -0.340030 | 8.166778 | 25 |  | OK |
| 8 | 5.527430 | 7.584692 | -0.112038 | 7.740249 | 25 |  | OK |
| 9 | 5.307243 | 6.829962 | +0.103223 | 6.970005 | 25 |  | OK |
| 10 | 5.338857 | 6.783708 | +0.156566 | 6.921749 | 25 |  | OK |
| 11 | 4.797815 | 6.349095 | -0.236185 | 6.475533 | 25 | Lowest validation MAE | OK |
| 12 | 4.835668 | 6.510475 | -0.316129 | 6.636887 | 25 |  | OK |
| 13 | 5.617383 | 7.258558 | +0.091069 | 7.407651 | 25 |  | OK |
| 14 | 5.734190 | 7.009005 | +0.605735 | 7.126771 | 25 |  | OK |
| 15 | 5.768688 | 7.055158 | +0.681730 | 7.166946 | 25 |  | OK |
| 16 | 5.792935 | 7.161839 | +0.940922 | 7.246163 | 25 |  | OK |
| 17 | 6.117630 | 7.479453 | +1.056950 | 7.557080 | 25 |  | OK |
| 18 | 6.372011 | 7.634552 | +1.010132 | 7.723477 | 25 |  | OK |
| 19 | 6.358696 | 7.435613 | +0.907537 | 7.532203 | 25 |  | OK |
| 20 | 6.432388 | 7.490253 | +0.859700 | 7.594186 | 25 |  | OK |
| 21 | 6.114650 | 7.209569 | +0.855634 | 7.306231 | 25 |  | OK |
| 22 | 6.287896 | 7.420350 | +0.772325 | 7.532230 | 25 |  | OK |
| 23 | 6.469310 | 7.722983 | +0.610332 | 7.857584 | 25 |  | OK |
| 24 | 6.879355 | 8.244009 | +0.373556 | 8.405364 | 25 |  | OK |
| 25 | 6.975959 | 8.363672 | +0.490700 | 8.521433 | 25 |  | OK |
| 26 | 6.882172 | 8.274277 | +0.150856 | 8.443495 | 25 |  | OK |
| 27 | 6.990518 | 8.401314 | -0.012610 | 8.574546 | 25 |  | OK |
| 28 | 7.125567 | 8.686006 | -0.059252 | 8.864911 | 25 |  | OK |
| 29 | 7.370410 | 8.904260 | -0.095047 | 9.087354 | 25 |  | OK |
| 30 | 7.399195 | 8.961627 | -0.214918 | 9.143792 | 25 |  | OK |

## chemotools — Glucose

**Cross-validation.** Candidates 1–10. Smallest centered training rank: 15. The two-component baseline MAE was 9.451865 g/L. The lowest validation MAE was 7.291452 g/L at one component.

| Components | MAE (g/L) | RMSE (g/L) | Signed bias (g/L) | SEP (g/L) | Samples | Marker | Status |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 7.291452 | 9.096959 | +0.230363 | 9.318620 | 21 | Lowest validation MAE | OK |
| 2 | 9.451865 | 12.310892 | +2.339473 | 12.385038 | 21 | 2-component baseline | OK |
| 3 | 8.128430 | 10.232880 | +1.364487 | 10.391945 | 21 |  | OK |
| 4 | 7.820549 | 9.730215 | +1.040784 | 9.913301 | 21 |  | OK |
| 5 | 7.907018 | 9.811323 | +1.207121 | 9.977232 | 21 |  | OK |
| 6 | 7.919284 | 9.830588 | +1.201908 | 9.997783 | 21 |  | OK |
| 7 | 7.921487 | 9.830099 | +1.198374 | 9.997724 | 21 |  | OK |
| 8 | 7.918620 | 9.827408 | +1.198901 | 9.994879 | 21 |  | OK |
| 9 | 7.918703 | 9.827449 | +1.198759 | 9.994939 | 21 |  | OK |
| 10 | 7.918723 | 9.827469 | +1.198752 | 9.994961 | 21 |  | OK |

## Verification

- Clicked **Run PLS** for all three choices against the running local Streamlit app with Turso data. Confirmed the comparison was below the button and the selected run appeared below the comparison. The only plot is for the selected run.
- For NIR ethanol, selected 3 and then 31 components. The selected model changed on each click. The first table retained all 30 default rows and the second added the 31-component row. The extra row had validation MAE 1.742168, RMSE 2.073261, signed bias +0.586998 and SEP 2.029430 g/L over 25 samples. The selected-run held-out test MAE changed from 3.709626 g/L at 3 components to 1.457179 g/L at 31 components.
- Switched to NIR glucose and chemotools glucose. Each had its own comparison and selected result. Switching back restored the ethanol result with 31 components. NIR showed separate held-out test metrics. Chemotools showed the selected count’s cross-validation metrics over 21 pooled predictions.
- Checked that the NIR held-out test indexes are disjoint from the training and validation indexes, that each chemotools calibration pair appears in validation once, and that SEP uses the sample standard deviation. All 70 default candidates and the extra ethanol candidate fitted successfully. Controlled inputs verified failure reporting and the smaller-count rule for exact MAE ties.
- Verified that the main app responded on localhost:8501. No requested verification remains open.

## Files changed

- `app.py` wires both PLS actions to one button and displays the comparison, status, and selected result.
- `nir_calibration.py` implements fixed-fold PLS fitting, pooled validation scoring, and the selected NIR test evaluation.
- `README.md` documents the component comparison.
- `PLS_COMPONENT_COMPARISON_REPORT.md` records the complete results and verification.
