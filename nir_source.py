"""Read the two published components of chemometrics::NIR without resampling."""

import json
from math import isfinite
from urllib.request import urlopen

import pandas as pd

NIR_URL = "https://filzmoserp.r-universe.dev/chemometrics/data/NIR/json"


def read_json(url):
    with urlopen(url, timeout=12) as response:
        return json.load(response)


def parse_nir(payload):
    if not isinstance(payload, dict) or set(payload) != {"xNIR", "yGlcEtOH"}:
        raise ValueError("Expected the xNIR and yGlcEtOH components.")

    x_rows, y_rows = payload["xNIR"], payload["yGlcEtOH"]
    if any(not isinstance(rows, list) or len(rows) != 166 for rows in (x_rows, y_rows)):
        raise ValueError("Expected 166 rows in each component.")

    spectral_fields = [f"X{wavelength}.0" for wavelength in range(1115, 2286, 5)]
    x_fields = [*spectral_fields, "_row"]
    y_fields = ["Glucose", "Ethanol"]
    for name, rows, fields, numeric in (
        ("xNIR", x_rows, x_fields, spectral_fields),
        ("yGlcEtOH", y_rows, y_fields, y_fields),
    ):
        if any(not isinstance(row, dict) or list(row) != fields for row in rows):
            raise ValueError(f"{name} field names or order differ from the expected source schema.")
        if any(type(row[field]) not in (int, float) or not isfinite(row[field])
               for row in rows for field in numeric):
            raise ValueError(f"{name} contains an invalid numeric measurement.")
    if any(not isinstance(row["_row"], str) or not row["_row"] for row in x_rows):
        raise ValueError("xNIR contains a missing or invalid source row label.")

    display_index = pd.RangeIndex(1, 167, name="Display index")
    return (
        pd.DataFrame(x_rows, columns=x_fields, index=display_index),
        pd.DataFrame(y_rows, columns=y_fields, index=display_index),
    )
