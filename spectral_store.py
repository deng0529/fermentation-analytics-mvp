"""Import the published spectra once and reconstruct their original pandas tables from Turso."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from importlib.metadata import version
from itertools import islice
import json

import numpy as np
import pandas as pd

from explorer_plots import MINUTES_PER_SPECTRUM, match_test_spectra
from nir_source import NIR_URL, parse_nir, read_json
from turso_database import DatasetError, TursoStatementError, connect, migrate

NIR = "chemometrics::NIR"
CHEMOTOOLS = "chemotools"
CHEMOTOOLS_URI = "https://chemotools.org/learn/datasets.html#the-fermentation-dataset"
TEST_COLUMNS = ["time", "glucose", "xylose", "acetic_acid", "ethanol", "furfural"]
PAIR_COLUMNS = ["spectrum_position", "lab_index", "lab_hour", "spectrum_hour", "delta_minutes", "glucose"]
MATCH_RULE = f"nearest estimated spectrum time; first at 0 h; {MINUTES_PER_SPECTRUM:g} min interval; in-range HPLC only; earlier spectrum wins ties"
SPLITS = {NIR: {"calibration": (166, 166)}, CHEMOTOOLS: {"train": (21, 21), "test": (1629, 34)}}
SPECTRUM_COLUMNS = "version_id, split, position, source_index, source_row_label, readings_json"


def encode(value):
    return json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"))


def load_upstream(dataset):
    if dataset == NIR:
        return NIR_URL, None, {"calibration": parse_nir(read_json(NIR_URL))}

    from chemotools.datasets import load_fermentation_test, load_fermentation_train

    return CHEMOTOOLS_URI, version("chemotools"), {
        "train": load_fermentation_train(),
        "test": load_fermentation_test(),
    }


def validate(dataset, frames):
    if frames.keys() != SPLITS[dataset].keys():
        raise ValueError("Unexpected splits")
    expected_refs = {"calibration": ["Glucose", "Ethanol"], "train": ["glucose"], "test": TEST_COLUMNS}
    expected_channels = (
        pd.Index([f"X{wavelength}.0" for wavelength in range(1115, 2286, 5)])
        if dataset == NIR else frames["train"][0].columns
    )
    channel_count = 235 if dataset == NIR else 1047
    for split, (spectra, references) in frames.items():
        signals = spectra.drop(columns="_row") if dataset == NIR else spectra
        if ((len(spectra), len(references)) != SPLITS[dataset][split]
                or list(references) != expected_refs[split]
                or len(signals.columns) != channel_count or not signals.columns.is_unique
                or not signals.columns.equals(expected_channels)):
            raise ValueError("Unexpected table dimensions or columns")
        if dataset == NIR:
            if list(spectra.columns) != [*expected_channels, "_row"] or spectra["_row"].isna().any():
                raise ValueError("Invalid NIR row labels")
        elif not np.isfinite(signals.columns.to_numpy(dtype=float)).all():
            raise ValueError("Invalid wavenumber")
        start, name = (1, "Display index") if dataset == NIR else (0, None)
        for frame in (spectra, references):
            if not frame.index.identical(pd.RangeIndex(start, start + len(frame), name=name)):
                raise ValueError("Unexpected source row order or index")
        for frame in (signals, references):
            if not all(pd.api.types.is_numeric_dtype(dtype) for dtype in frame.dtypes):
                raise ValueError("Unexpected measurement type")
            if not np.isfinite(frame.to_numpy(dtype=float)).all():
                raise ValueError("Non-finite measurement")


def column_schema(frame):
    return {
        "labels": frame.columns.tolist(),
        "label_type": str(frame.columns.dtype),
        "types": [str(dtype) for dtype in frame.dtypes],
    }


def insert_rows(session, table, columns, rows, width, chunk_size):
    records = iter(rows)
    row_sql = "(" + ",".join("?" for _ in range(width)) + ")"
    while chunk := list(islice(records, chunk_size)):
        sql = f"INSERT INTO {table} ({columns}) VALUES " + ",".join([row_sql] * len(chunk))
        session.execute((sql, tuple(value for row in chunk for value in row)))


def prepare_snapshot(dataset, source_uri, package_version, frames):
    validate(dataset, frames)
    nir = dataset == NIR
    first_spectra = next(iter(frames.values()))[0]
    signals = first_spectra.drop(columns="_row") if nir else first_spectra
    pairs = None if nir else match_test_spectra(*frames["test"])
    references_schema = {}
    schema = {
        "spectra": {**column_schema(signals), "channel_unit": "nm" if nir else "cm⁻¹",
                    "signal": "first derivative of absorbance" if nir else "absorbance"},
        "references": references_schema,
        "source_index_start": first_spectra.index.start,
        "source_index_name": first_spectra.index.name,
        "row_label_type": str(first_spectra["_row"].dtype) if nir else None,
        "alignment_count": 0 if pairs is None else len(pairs),
    }
    spectra_rows, reference_rows, alignment_rows = [], [], []
    for split, (spectra, references) in frames.items():
        features = spectra.drop(columns="_row") if nir else spectra
        if column_schema(features) != column_schema(signals):
            raise ValueError("Spectral column types differ between splits")
        references_schema[split] = {**column_schema(references), "units": {
            name: "h" if name == "time" else "g/L" for name in references.columns
        }}
        labels = spectra["_row"] if nir else [None] * len(spectra)
        spectra_rows.extend(
            (split, pos, index, label, encode(values))
            for pos, (index, label, values) in enumerate(zip(
                spectra.index, labels, features.itertuples(index=False, name=None), strict=True
            ))
        )
        reference_rows.extend(
            (split, pos, index, encode(values))
            for pos, (index, values) in enumerate(zip(
                references.index, references.itertuples(index=False, name=None), strict=True
            ))
        )
    if pairs is not None:
        alignment_rows = [
            ("test", row.spectrum_position, row.lab_index, row.spectrum_hour, row.lab_hour, MATCH_RULE, 1)
            for row in pairs.itertuples(index=False)
        ]
    digest = sha256()
    for entry in ((dataset, source_uri, package_version, schema), *spectra_rows, *reference_rows, *alignment_rows):
        digest.update(encode(entry).encode())
        digest.update(b"\n")
    return digest.hexdigest(), encode(schema), spectra_rows, reference_rows, alignment_rows


def snapshot_header(database, dataset):
    rows, = database.execute(("SELECT version_id, schema_json FROM dataset_versions WHERE dataset = ?", (dataset,)))
    return rows[0] if rows else None


def save_snapshot(database, dataset, source_uri, package_version, prepared):
    version_id, schema, spectra, references, alignment = prepared
    # Spectra are staged on the HTTP connection before the short publication transaction.
    # Closing the connection drops the temporary rows, including after any failure.
    with database.session() as session:
        session.execute(
            ("PRAGMA foreign_keys = ON", ()),
            ("CREATE TEMP TABLE staged_spectra (version_id, split, position, source_index, source_row_label, readings_json)", ()),
        )
        insert_rows(session, "staged_spectra", SPECTRUM_COLUMNS,
                    ((version_id, *row) for row in spectra), 6, 48)
        session.execute(("BEGIN IMMEDIATE", ()))
        session.execute(
            ("INSERT INTO dataset_versions (version_id, dataset, source_uri, package_version, schema_json) "
             "VALUES (?, ?, ?, ?, ?)", (version_id, dataset, source_uri, package_version, schema)),
            (f"INSERT INTO spectral_inputs ({SPECTRUM_COLUMNS}) SELECT {SPECTRUM_COLUMNS} FROM staged_spectra", ()),
        )
        insert_rows(session, "reference_outputs", "version_id, split, position, source_index, values_json",
                    ((version_id, *row) for row in references), 5, 200)
        insert_rows(session, "test_alignment", "version_id, split, spectrum_position, reference_position, "
                    "estimated_spectrum_hour, recorded_hplc_hour, matching_rule, approximate",
                    ((version_id, *row) for row in alignment), 8, 200)
        session.execute(("COMMIT", ()), close=True)


def read_table(database, table, version_id, split, count, columns):
    page_size = 64
    sql = (f"SELECT {columns} FROM {table} "
           "WHERE version_id = ? AND split = ? AND position >= ? AND position < ? ORDER BY position")

    def read_page(start):
        rows, = database.execute((sql, (version_id, split, start, start + page_size)))
        return rows

    with ThreadPoolExecutor(max_workers=5) as workers:
        rows = [row for page in workers.map(read_page, range(0, count, page_size)) for row in page]
    if [row[0] for row in rows] != list(range(count)):
        raise ValueError("Missing or unexpected source positions")
    totals, = database.execute((f"SELECT COUNT(*) FROM {table} WHERE version_id = ? AND split = ?", (version_id, split)))
    if totals != [(count,)]:
        raise ValueError("Unexpected stored row count")
    return rows


def restore_frame(rows, metadata, schema):
    start = schema["source_index_start"]
    index = pd.RangeIndex(start, start + len(rows), name=schema["source_index_name"])
    if [row[1] for row in rows] != list(index):
        raise ValueError("Unexpected stored source index")
    values = [json.loads(row[2]) for row in rows]
    labels = pd.Index(metadata["labels"], dtype=metadata["label_type"])
    if any(not isinstance(row, list) or len(row) != len(labels) for row in values):
        raise ValueError("Unexpected stored row width")
    types = dict(zip(labels, metadata["types"], strict=True))
    return pd.DataFrame(values, index=index, columns=labels).astype(types).copy()


def restore_alignment(database, version_id, references, expected_count, spectrum_count):
    rows, = database.execute((
        "SELECT spectrum_position, reference_position, recorded_hplc_hour, estimated_spectrum_hour, "
        "matching_rule, approximate FROM test_alignment WHERE version_id = ? AND split = 'test' ORDER BY reference_position",
        (version_id,),
    ))
    if len(rows) != expected_count or any(
        not 0 <= spectrum < spectrum_count or not 0 <= lab < len(references)
        or lab_hour != references.iloc[lab]["time"] or spectrum_hour != spectrum * MINUTES_PER_SPECTRUM / 60
        or rule != MATCH_RULE or approximate != 1
        for spectrum, lab, lab_hour, spectrum_hour, rule, approximate in rows
    ):
        raise ValueError("Invalid stored approximate alignment")
    values = [
        (spectrum, references.index[lab], lab_hour, spectrum_hour,
         (spectrum_hour - lab_hour) * 60, float(references.iloc[lab]["glucose"]))
        for spectrum, lab, lab_hour, spectrum_hour, _, _ in rows
    ]
    return pd.DataFrame(values, columns=PAIR_COLUMNS)


def read_snapshot(database, dataset, header):
    version_id, schema_json = header
    try:
        schema = json.loads(schema_json)
        frames = {}
        for split, (spectral_count, reference_count) in SPLITS[dataset].items():
            spectral_rows = read_table(database, "spectral_inputs", version_id, split, spectral_count,
                                       "position, source_index, readings_json, source_row_label")
            reference_rows = read_table(database, "reference_outputs", version_id, split, reference_count,
                                         "position, source_index, values_json")
            spectra = restore_frame(spectral_rows, schema["spectra"], schema)
            if dataset == NIR:
                spectra["_row"] = pd.array([row[3] for row in spectral_rows], dtype=schema["row_label_type"])
            references = restore_frame(reference_rows, schema["references"][split], schema)
            frames[split] = spectra, references
        validate(dataset, frames)
        pairs = None
        if dataset == CHEMOTOOLS:
            pairs = restore_alignment(database, version_id, frames["test"][1], schema["alignment_count"],
                                      len(frames["test"][0]))
        return frames, pairs
    except (ValueError, KeyError, TypeError, OverflowError):
        raise DatasetError("The stored Turso snapshot is incomplete or does not match the expected source schema.") from None


def load_dataset(dataset, *, database=None):
    """Read a committed snapshot, or validate, import and re-read a genuinely missing dataset."""
    _, frames, pairs = load_versioned_dataset(dataset, database=database)
    return frames, pairs


def load_versioned_dataset(dataset, *, database=None):
    """Return the content identifier of the same snapshot used to reconstruct the tables."""
    database = database if database is not None else connect()
    header = snapshot_header(database, dataset)
    if header is None:
        try:
            source_uri, package_version, frames = load_upstream(dataset)
            prepared = prepare_snapshot(dataset, source_uri, package_version, frames)
        except (ImportError, OSError, ValueError, TypeError, KeyError) as error:
            raise DatasetError(f"The upstream {dataset} dataset could not be loaded or failed validation.") from error
        try:
            save_snapshot(database, dataset, source_uri, package_version, prepared)
        except TursoStatementError:
            # A concurrent import may have won the unique dataset key.
            header = snapshot_header(database, dataset)
            if header is None:
                raise
        else:
            header = snapshot_header(database, dataset)
        if header is None:
            raise DatasetError("Turso did not return the committed dataset snapshot. Retry the load.")
    frames, pairs = read_snapshot(database, dataset, header)
    return header[0], frames, pairs


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Prepare a spectral snapshot in Turso.")
    parser.add_argument("--dataset", choices=tuple(SPLITS), default=NIR,
                        help="Dataset to prepare. The active NIR snapshot is the default.")
    source = parser.parse_args().dataset
    try:
        database = connect()
        migrate(database)
        splits, matches = load_dataset(source, database=database)
        for split, (spectra, references) in splits.items():
            print(f"{source} {split} — inputs {spectra.shape}, references {references.shape}")
        if matches is not None:
            print(f"{len(matches)} approximate HPLC matches")
    except DatasetError as error:
        raise SystemExit(str(error)) from None
