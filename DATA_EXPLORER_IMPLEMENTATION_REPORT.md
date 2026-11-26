# Data Explorer implementation report

Verified locally on 24 November 2026. The Streamlit server was running and its health endpoint returned `ok`. [Open Data Explorer locally](http://127.0.0.1:8502/data-explorer).

## What happened to Validation

The project directory is untracked in the enclosing Git repository, and the path-scoped Git history returned no commits. The archived HTML prototype and the current Streamlit code provided the evidence for this review.

| Previous functionality | Current location and status |
| --- | --- |
| The archived **Data & Validation** view showed dataset version, import status, record count, and validation-result placeholders. It also listed illustrative run configurations. It showed no dataset-validation charts or executed model checks. | **Data Explorer** now shows live NIR dimensions, column meanings, missing-value counts, and the X–Y pairing evidence. **Spectral Calibration** holds illustrative run history. |
| **Spectral Calibration** showed predicted-versus-reference rows and PLS/SVR MAE, RMSE, signed bias, and evaluated sample counts. It also showed the chemotools glucose replay with PLS, SVR, and HPLC values. | The same outputs remain in **Spectral Calibration**. The app computes the metrics from paired illustrative values with preset predictions. The replay curves and HPLC points are illustrative. |

The app has no trained PLS/SVR validation or separate Model Validation page. Training and fitted-model evaluation remain planned.

## Source and table structure

The inventory lists three datasets with three columns: **Data source**, **Purpose**, and **Data type**. The public dataset names link to their sources, and the NIR link returned HTTP 200 with the expected JSON. [NIR JSON endpoint](https://filzmoserp.r-universe.dev/chemometrics/data/NIR/json) · [chemotools dataset documentation](https://chemotools.org/learn/datasets.html)

| Component | Verified dimensions | Meaning |
| --- | --- | --- |
| `xNIR` | 166 rows × 235 spectral columns, plus the source `_row` field | Each row contains the spectrum of one alcoholic fermentation mash sample. Each spectral cell is the published first derivative of NIR absorbance at its wavelength. |
| `yGlcEtOH` | 166 rows × 2 columns | Each row contains concentrations for one mash sample. The exact columns, in order, are `Glucose` and `Ethanol`. Both are reference concentrations in g/L. |

The verified spectral headers include `X1115.0` (first, 1115 nm), `X1120.0` (1120 nm), and `X2285.0` (last, 2285 nm). The final JSON field `_row` is a source-provided row label and is excluded from the 235 spectral inputs. The app adds a **Display index** to both tables. It is excluded from all source column counts. The loaded tables contained zero missing values. [NIR package documentation](https://search.r-project.org/CRAN/refmans/chemometrics/html/NIR.html)

### X–Y pairing

Pair the same row position in the two published components. The package’s stepwise-regression example takes rows 1–30 from both components and directly combines them by position. The JSON supplies `_row` labels only in `xNIR`, so independent identifier matching is unavailable. The tables retain source order and share a 1-based **Display index**. [Package pairing example](https://filzmoserp.r-universe.dev/chemometrics/doc/manual.html#stepwise)

| Display index | Original `_row` | `X1115.0` | `X1120.0` | `X2285.0` | `Glucose` (g/L) | `Ethanol` (g/L) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `R1 zaM 1` | 0.0032 | 0.0040 | −0.0195 | 9.781 | 40.304 |
| 166 | `VM3_7z` | 0.0026 | 0.0035 | −0.0180 | 3.420 | 88.140 |

The app shows the first pair above the complete tables. Both boundary records were checked against the JSON.

## Verification

- Local Chrome passed the three-column inventory, dataset count, public NIR link, two-row summary, and paired example checks. Both data grids scrolled vertically, and the spectral grid scrolled horizontally.
- Streamlit AppTest compared every displayed source field and value, in order, with a fresh upstream JSON response. Both complete tables matched, and both display indices covered 1–166.
- A calibration preview still showed metrics for both PLS and SVR and appeared in illustrative run history.
- The local server at `127.0.0.1:8502` returned `ok` after verification.

## Files changed

- [app.py](app.py) renders the simplified inventory and the NIR explanation, dataset checks, and paired example before the full data grids.
- [nir_source.py](nir_source.py) removes the unused package-metadata endpoint constant. The cached JSON load and schema checks continue to use the published NIR endpoint.
- This report records the implementation and verification results.

Chemotools ingestion, Turso import, and fitted-model evaluation remain pending. The NIR endpoint provides positional pairing evidence and no shared row identifier for an independent join.
