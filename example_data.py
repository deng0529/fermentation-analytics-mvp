"""Local Step 1 fixtures. All concentrations, predictions and traces are illustrative."""

from math import sin, sqrt

TARGET = 130.0
FORECAST_HOUR = 30
DISCHARGE_HOUR = 36
BATCHES = {
    "F-0607 · Shortfall": (119.2, 121.1, 120.4),
    "F-0608 · On target": (134.6, 132.7, 133.1),
    "F-0609 · Recovery": (125.8, 131.8, 131.3),
}
SOURCES = {
    "chemometrics::NIR": {
        "unit": "nm",
        "channels": [1115, 1220, 1330, 1430, 1540, 1650, 1760, 1870, 1980, 2090, 2200, 2285],
        "targets": {"Ethanol": [12, 19, 27, 33, 41, 48], "Glucose": [3, 6, 10, 16, 23, 31]},
        "type": "First-derivative NIR absorbance",
        "purpose": "Model 1A · Ethanol and glucose calibration",
        "url": "https://search.r-project.org/CRAN/refmans/chemometrics/html/NIR.html",
    },
}
REPLAY = [
    {"Hour": h, "PLS": pls, "SVR": svr, "HPLC": hplc}
    for h, pls, svr, hplc in zip(
        range(0, 25, 4), [41, 36, 31, 24, 17, 10, 5],
        [40, 37, 30, 23, 16, 11, 6], [40, None, 30, None, 17, None, 5],
        strict=True,
    )
]
OFFSETS = {"PLS": [.8, -1.1, .6, 1.4, -1.8, .9], "SVR": [-.5, .7, -.9, .3, 1.1, -.6]}


def batch_readings(batch_id):
    _, endpoint, _ = BATCHES[batch_id]
    return [
        {
            "Hour": hour,
            "Ethanol estimate": round(endpoint * (1 - (1 - hour / DISCHARGE_HOUR) ** 1.4), 1),
            "Glucose estimate": round(5 + (175 - endpoint / 3) * (1 - hour / DISCHARGE_HOUR) ** 1.6, 1),
            "Temperature (°C)": round(30 + .32 * sin(hour / 5), 1),
            "pH": round(5.4 - hour / 34, 2),
        }
        for hour in range(DISCHARGE_HOUR + 1)
    ]


def sample_pairs(source, compound):
    return [
        {"Sample ID": f"S-{index:02}", "Reference (g/L)": value}
        for index, value in enumerate(SOURCES[source]["targets"][compound], start=1)
    ]


def preview_comparison(source, compound):
    rows = sample_pairs(source, compound)
    for i, row in enumerate(rows):
        for model, offsets in OFFSETS.items():
            row[model] = round(row["Reference (g/L)"] + offsets[i], 1)
    metrics = []
    for model in OFFSETS:
        errors = [row[model] - row["Reference (g/L)"] for row in rows]
        n = len(errors)
        metrics.append({
            "Model": model,
            "MAE (g/L)": round(sum(map(abs, errors)) / n, 2),
            "RMSE (g/L)": round(sqrt(sum(error ** 2 for error in errors) / n), 2),
            "Bias (g/L)": round(sum(errors) / n, 2),
            "Evaluated samples": n,
        })
    return rows, metrics
