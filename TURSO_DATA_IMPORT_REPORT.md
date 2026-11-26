# Turso spectral data import

The app is running at [http://localhost:8501](http://localhost:8501). Data Explorer and Preprocessing & Feature Selection use the same database-first loader.

## Tables created

| Table | Contents | Actual rows |
| --- | --- | ---: |
| `dataset_versions` | Source URL, installed package version where available, import timestamp, content hash and ordered column schema | 2 |
| `spectral_inputs` | Dataset version, split, original position and index, NIR row label where present, and an ordered JSON array of readings | 1,816 |
| `reference_outputs` | Dataset version, split, original position and index, and the source reference values in column order | 221 |
| `test_alignment` | Approximate matches keyed to the separate spectrum and HPLC records, with both times and the matching rule | 34 |

| Source and split | Spectral rows × channels | Reference rows × columns | Approximate test matches |
| --- | ---: | ---: | ---: |
| chemometrics::NIR calibration | 166 × 235 | 166 × 2 | — |
| chemotools training | 21 × 1,047 | 21 × 1 | — |
| chemotools test | 1,629 × 1,047 | 34 × 6 | 34 |

The reconstructed NIR spectral DataFrame has 236 columns, including the `_row` metadata column. Its reference columns are `Glucose` and `Ethanol`. Chemotools 0.5.0 supplies the training column `glucose` and the six test fields `time`, `glucose`, `xylose`, `acetic_acid`, `ethanol`, and `furfural`. Test spectra and HPLC retain independent indexes. The approximate mapping uses the nearest eligible spectrum at a nominal 1.25-minute cadence from zero and records both times. The NIR data endpoint supplies no package version with the table, so its snapshot records the source URI and the content hash.

## Checks performed

- Applied the migration repeatedly to the configured Turso database. It created the four tables on the first run and preserved them on repeated runs.
- Confirmed that both datasets were initially absent. NIR imported and read back successfully. The first chemotools attempt was rejected at the alignment insert because of the HTTP float encoding. Turso rolled back the transaction. After correction, the retry confirmed the snapshot was still absent, then imported and read it back successfully.
- Compared the reconstructed spectral and reference DataFrames to the original loader output with exact pandas equality checks, including every value, column name and order, dtype, and index type, name and order. Compared all 34 stored alignment records to the existing matcher output. Calibration and training pairings matched their original source positions.
- Repeated the reads with upstream loading forced to raise. Counts remained identical and there was one version per source. A live rejected token and a separate connection failure both produced explicit errors and triggered no upstream request.
- Started a fresh local Streamlit test process with upstream loading forced to raise. Exercised NIR ethanol, NIR glucose, and chemotools glucose in both Data Explorer and Preprocessing & Feature Selection. Opened the chemotools test timeline and the stored 34-pair spectral overlay. The main app responded at localhost:8501.

Concurrent imports from two separate processes and a separate read-only credential were not exercised live. The database enforces one published version per dataset. Imports publish the manifest, spectra, references, and alignment in one transaction.

## Files changed

- `app.py` uses the shared database-first loader on both spectral pages and displays the stored test alignment.
- `spectral_store.py` reuses the source loaders, validates and imports missing snapshots, and reconstructs the tables.
- `turso_database.py` reads local connection settings and runs authenticated parameterised Turso requests.
- `migrations/001_spectral_snapshots.sql` defines the repeatable schema.
- `requirements.txt` adds the local environment file reader.
- `.gitignore` excludes local credential files.
- `README.md` documents local setup and the import command.
- `TURSO_DATA_IMPORT_REPORT.md` records the import and verification.
