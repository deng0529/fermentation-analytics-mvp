"""Causal discharge forecast features, synthetic training, and evaluation."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from example_data import DISCHARGE_HOUR, TARGET
from nir_calibration import error_metrics

HOUR = 60
WINDOW = 2 * HOUR
DISCHARGE = DISCHARGE_HOUR * HOUR
FEATURES = ("Latest ethanol (g/L)", "Ethanol slope (g/L/h)", "Time remaining (h)")
MODEL_VERSION = "ethanol-only-v2"
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
SEED = 2601
SPLIT_SIZES = {"Training": 240, "Validation": 80, "Held-out test": 80}


@dataclass(frozen=True)
class Reading:
    minute: int
    released: int
    ethanol: float
    source: str
    temperature: float | None = None
    ph: float | None = None
    source_row: str | None = None


def forecast_features(readings, issue, discharge, cadence):
    """Use the two-hour change between timely observations at the window boundaries."""
    if issue >= discharge:
        return None, "The scheduled discharge time has been reached."
    if issue < WINDOW:
        return None, "Waiting for two hours of usable concentration history."
    available = sorted((row for row in readings if row.released <= issue and row.minute <= issue),
                       key=lambda row: row.minute)
    if not available or issue - available[-1].minute >= cadence:
        return None, "The latest concentration reading is missing or stale."
    latest = available[-1]
    earlier = next((row for row in reversed(available) if row.minute <= latest.minute - WINDOW), None)
    if earlier is None or latest.minute - WINDOW - earlier.minute >= cadence:
        return None, "A timely reading at the start of the two-hour window is unavailable."
    span = (latest.minute - earlier.minute) / HOUR
    values = (latest.ethanol, (latest.ethanol - earlier.ethanol) / span, (discharge - issue) / HOUR)
    if not np.isfinite(values).all():
        return None, "The two-hour window contains unavailable concentrations."
    return dict(zip(FEATURES, values)), None


def issue_forecasts(model, readings, now, discharge, cadence):
    windows = []
    issues = []
    reason = "Waiting for two hours of usable concentration history."
    for issue in range(WINDOW, min(now + 1, discharge), HOUR):
        features, reason = forecast_features(readings, issue, discharge, cadence)
        if features is not None:
            issues.append(issue)
            windows.append(features)
    if not windows:
        return [], reason
    predictions = model.predict(pd.DataFrame(windows, columns=FEATURES))
    history = [{"Issue minute": issue, "Predicted ethanol (g/L)": float(prediction), "features": features}
               for issue, prediction, features in zip(issues, predictions, windows, strict=True)]
    return history, reason


def generate_batch(rng, batch_id):
    """Generate statistical replay data with independently varied trajectories and assay noise."""
    hours = np.arange(DISCHARGE_HOUR + 1)
    progress = hours / DISCHARGE_HOUR
    rate = rng.uniform(3.0, 5.0)
    bend = rng.uniform(10, 40)
    late_shift = rng.normal(0, 7)
    ethanol = rng.uniform(0, 5) + rate * hours - bend * progress**2 + late_shift * progress**4
    measured_ethanol = ethanol + rng.normal(0, 1.2, len(hours))
    readings = [
        Reading(int(hour) * HOUR, int(hour) * HOUR, e, batch_id)
        for hour, e in zip(hours, measured_ethanol, strict=True)
    ]
    reference = float(ethanol[-1] + rng.normal(0, 1))
    return readings, reference


def train_model_2():
    rng = np.random.default_rng(SEED)
    splits = {}
    for split, count in SPLIT_SIZES.items():
        rows = []
        for index in range(count):
            batch_id = f"model2-{split.lower().replace(' ', '-')}-{index:03}"
            readings, reference = generate_batch(rng, batch_id)
            for issue in range(WINDOW, DISCHARGE, HOUR):
                features, reason = forecast_features(readings, issue, DISCHARGE, HOUR)
                if features is None:
                    raise ValueError(reason)
                rows.append({"Batch": batch_id, "Reference (g/L)": reference, **features})
        splits[split] = pd.DataFrame(rows)

    train, validation, test = (splits[name] for name in SPLIT_SIZES)
    columns = list(FEATURES)
    reference = "Reference (g/L)"
    candidates = {}
    for alpha in ALPHAS:
        model = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
        model.fit(train[columns], train[reference])
        scores = error_metrics(validation[reference], model.predict(validation[columns]))
        candidates[alpha] = (scores["MAE"], model)
    selected = min(candidates, key=lambda alpha: candidates[alpha][0])
    model = candidates[selected][1]
    held_out = test.copy()
    held_out["Ridge"] = model.predict(test[columns])
    latest, slope, remaining = FEATURES
    held_out["Trend baseline"] = test[latest] + test[slope] * test[remaining]
    metrics = []
    for lead in (12, 6, 2):
        rows = held_out.loc[held_out[FEATURES[-1]] == lead]
        actual_shortfall = rows[reference] < TARGET
        for method in ("Ridge", "Trend baseline"):
            predicted_shortfall = rows[method] < TARGET
            errors = error_metrics(rows[reference], rows[method])
            metrics.append({"Lead (h)": lead, "Method": method, "Samples": errors["Samples"],
                            "MAE (g/L)": errors["MAE"],
                            "MSE ((g/L)²)": float(np.square(rows[method] - rows[reference]).mean()),
                            "RMSE (g/L)": errors["RMSE"],
                            "Bias (g/L)": errors["Bias"],
                            "Missed shortfalls": int((actual_shortfall & ~predicted_shortfall).sum()),
                            "Actual shortfalls": int(actual_shortfall.sum()),
                            "False warnings": int((~actual_shortfall & predicted_shortfall).sum()),
                            "Actual at or above target": int((~actual_shortfall).sum())})
    validation_scores = pd.DataFrame([{"Alpha": alpha, "Validation MAE (g/L)": candidate[0]}
                                      for alpha, candidate in candidates.items()])
    sizes = pd.DataFrame([{"Split": name, "Batches": frame["Batch"].nunique(), "Windows": len(frame),
                           "X shape": f"{len(frame):,} × {len(FEATURES)}", "y shape": f"({len(frame):,},)"}
                          for name, frame in splits.items()])
    return model, validation_scores, held_out, pd.DataFrame(metrics), sizes
