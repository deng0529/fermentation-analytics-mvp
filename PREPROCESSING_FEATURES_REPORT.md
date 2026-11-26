# Preprocessing & Feature Selection

## Files changed

- `app.py` shows the model inputs, output, source preprocessing, and split or test workflow. The existing confirmation action passes the dataset and target configuration to Model Training & Validation.
- `README.md` describes the updated workflow.
- `PREPROCESSING_FEATURES_REPORT.md` records the configuration and verification.

## chemometrics::NIR

| Loaded data | Dimensions and configuration |
| --- | --- |
| `xNIR` | 166 samples × 235 spectral features. The JSON also includes `_row` with source row labels. |
| `yGlcEtOH` | 166 samples × 2 reference columns in g/L, named `Glucose` and `Ethanol`. |
| Model inputs | All 235 channels in published order for both targets, from `X1115.0` through `X2285.0`. |
| Model target and output | 166 samples × 1 lab reference from the selected source column. Each prediction is one concentration in g/L. |

The package documents the values as first derivatives of NIR absorbance. The 1115 nm channel is displayed as `X1115` in the explanation and arrives as `X1115.0` in the JSON. The loaded first sample’s value in that column was 0.0032. The page applies no additional transformation. [chemometrics NIR reference](https://search.r-project.org/CRAN/refmans/chemometrics/html/NIR.html)

The loaded features and both reference columns contained zero missing and zero non-finite values. Both tables had 166 rows and the same display indexes. The source reference table supplies no independent sample IDs, so the check verifies pairing by published row position.

The previous app described a holdout without assigning rows. The new **Planned split** shuffles the shared one-based display indexes with Python’s seeded random generator using seed 42. The 116 training pairs fit the model, the 25 validation pairs guide settings, and the 25 test pairs evaluate the final model. The three partitions are disjoint and cover all 166 rows. Both confirmed targets carry the same assignments for PLS and SVR.

## chemotools fermentation

| Loaded data | Actual dimensions |
| --- | --- |
| Training spectra | 21 × 1,047 |
| Training references | 21 × 1, source column `glucose` |
| Test spectra | 1,629 × 1,047 |
| Test HPLC table | 34 × 6, including `time` in elapsed hours and `glucose` in g/L |

The installed chemotools 0.5.0 pandas loaders read the packaged CSV values directly and cast spectral column names to numeric wavenumbers. Training and test channels matched in source order. Training spectra and references shared the 0–20 row index. The spectral inputs, training glucose, and test `time` and `glucose` fields were finite. The page uses all 1,047 supplied ATR-FTIR absorbance readings at wavenumbers in cm⁻¹ and applies no additional preprocessing. The package tutorial applies its preprocessing after loading. The dataset guide lists 35 test references, while the installed loader returns 34. [Dataset guide](https://chemotools.org/learn/datasets.html#the-fermentation-dataset) · [Training guide](https://chemotools.org/learn/pls_regression.html#preprocessing-the-training-data)

PLS and SVR will choose settings by cross-validation within the 21 paired training samples. The supplied test run stays separate. Each fitted model will produce 1,629 glucose predictions. Evaluation will estimate spectrum times from acquisition order at a nominal cadence of 1.25 minutes, starting at zero, and select the prediction nearest each eligible HPLC time. Alignment is approximate and shared by both methods, with up to 34 comparisons per model. The existing Data Explorer matcher found 34 approximate source pairs for this package version. Fitted evaluation will report the actual number of matched predictions. The Data Explorer pairing tables retain their existing code.

## Local verification and training handoff

Ran Streamlit 1.67.0 locally and exercised the three views through its agent API with the live R-universe NIR feed and the installed chemotools dataset. Checked the dimensions, exact target names, source preprocessing statements, split counts, chemotools test workflow, and confirmation handoff to Model Training & Validation. A separate Streamlit AppTest check inspected the confirmed configuration and verified identical source-order channels and complete, paired NIR split membership for both targets. It also verified all 1,047 ordered chemotools channels and the exact lowercase target column.

Model Training & Validation receives the selected source target name, ordered channels and, for NIR, the explicit partition indexes and seed. Fitting, prediction, selection of matched model outputs, and fitted accuracy metrics remain to be implemented there. The existing six-sample illustrative comparison remains available as a preview.
