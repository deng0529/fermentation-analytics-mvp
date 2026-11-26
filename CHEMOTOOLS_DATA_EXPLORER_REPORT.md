# Chemotools Data Explorer implementation report

Verified on 24 November 2026 using the project’s Windows Python environment and **chemotools 0.5.0**. Streamlit is running at [Data Explorer](http://127.0.0.1:8502/data-explorer). Its health endpoint returned `ok` after the browser checks.

## Package data and display

The explorer loads the pandas DataFrames returned by `chemotools.datasets.load_fermentation_train()` and `chemotools.datasets.load_fermentation_test()`. The official dataset page is linked from the existing three-column inventory. Model 1B uses this dataset to estimate glucose concentration from ATR mid-infrared spectra. [Official fermentation dataset](https://chemotools.org/learn/datasets.html#the-fermentation-dataset)

| Table | Rows × data columns | Loader index | Each row represents |
| --- | ---: | --- | --- |
| Training spectra | 21 × 1,047 | 0–20 | One synthetic calibration spectrum |
| Training glucose references | 21 × 1 | 0–20 | One HPLC reference for a calibration sample |
| Test spectra | 1,629 × 1,047 | 0–1,628 | One online spectrum in acquisition order |
| Test glucose references | 34 × 6 | 0–33 | One offline HPLC observation, with elapsed time and other analytes |

The **Source index** in each grid displays the unnamed, zero-based index returned by its loader. It is excluded from the data-column counts. The spectra frames use the same 1,047 float headers, including `428.0`, `429.0`, and `1833.0`, which are wavenumbers in cm⁻¹. The cells are the packaged absorbance values. The glucose column is exactly `glucose` in both HPLC tables and is measured in g/L. The test HPLC columns are `time`, `glucose`, `xylose`, `acetic_acid`, `ethanol`, and `furfural`, in that order. [Training guide and spectral axis units](https://chemotools.org/learn/pls_regression.html#visualizing-the-training-data)

## Pairing and timing

- **Training** pairs each spectrum with the glucose reference at the same row position. The official guide uses the reference at each spectrum’s position, and the loader returns identical 0–20 indexes. At index 0, the `428.0` spectral cell is **0.493506** and the paired `glucose` reference is **1.664707074 g/L**. [Training guide](https://chemotools.org/learn/pls_regression.html#loading-the-training-data)
- **Test** spectra come in acquisition order with a positional index and no per-spectrum time field. The HPLC frame supplies elapsed hours in a separate `time` column, with uneven intervals. Its first, second, and last times are **0.0**, **0.666666667**, and **33.88333333** hours. The dataset guide describes spectra about every 1.25 minutes and HPLC sampling roughly hourly. The app preserves the two indexes independently and displays the original values without a positional join or generated timestamps. [Dataset guide](https://chemotools.org/learn/datasets.html#the-test-set) · [Glucose monitoring tutorial](https://chemotools.org/learn/pls_regression.html#applying-the-model)

The documentation describes 35 test references and gives approximate spectral sampling intervals of both 1.25 and 1.5 minutes in different passages. The installed 0.5.0 loader returns 34 HPLC rows and supplies no exact per-spectrum times. The explorer uses the packaged shape and recorded HPLC times. Absolute timestamps and an exact spectrum-to-HPLC alignment remain unverified.

## Verification results

- Streamlit AppTest compared all four grid payloads with fresh calls to the official loaders. Exact DataFrame equality passed for every value, header and header type, index, and row order.
- Boundary values below were checked at the first and last source indexes. The package returned zero missing values across the four frames.
- Local Chrome confirmed the official inventory link, NIR → chemotools → NIR switching, the four summary dimensions, the training pair, both tabs, both horizontal spectral scrollbars, and vertical scrolling in the test spectrum grid.
- The NIR grids still matched the published JSON. A simulated chemotools loader failure displayed the expected error. `pip check` reported no broken requirements, and the local server returned `ok`.

| Table | First record | Last record |
| --- | --- | --- |
| Training spectra | Index 0, `428.0` = 0.493506, `429.0` = −0.383721, `1833.0` = 0 | Index 20, `428.0` = 0.285714, `429.0` = −0.069767, `1833.0` = 0 |
| Training glucose references | Index 0, `glucose` = 1.664707074 | Index 20, `glucose` = 4.817912411 |
| Test spectra | Index 0, `428.0` = 1.878788, `429.0` = 1.185065, `1833.0` = 0 | Index 1,628, `428.0` = 1.0, `429.0` = 1.0, `1833.0` = 1 |
| Test glucose references | Index 0, `time` = 0.0, `glucose` = 44.41567094 | Index 33, `time` = 33.88333333, `glucose` = 4.0 |

## Files changed

- [app.py](app.py) adds the cached package loader, summary, pairing and timing explanation, and full data grids.
- [requirements.txt](requirements.txt) pins the verified chemotools 0.5.0 package.
- [README.md](README.md) describes how the two datasets are loaded.
- This report records the source findings and local checks.

Model training and Turso import remain outside this implementation.
