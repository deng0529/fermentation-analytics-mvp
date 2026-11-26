"""Replay identities, timed observations, and the illustrative spectral generator."""

import numpy as np
import pandas as pd

from example_data import BATCHES, batch_readings
from model_2 import DISCHARGE, HOUR, Reading, issue_forecasts

SYNTHETIC = "Synthetic batch replay"
SPECTRAL = "Model 1 spectral replay"
SIMULATED_SPECTRA = "Synthetic spectral batch"
PUBLIC_SEQUENCE = "chemometrics::NIR · 166 source rows"
SPECTRAL_BATCH = "SIM-NIR-01 · Illustrative spectrum demo"
SPECTRAL_CADENCE = 2
SPECTRAL_SEED = 7291
SPECTRAL_VERSION = "ethanol-template-interpolation-v1"
SPECTRAL_TARGET = 80.0
SCENARIOS = {
    "F-0607 · Shortfall": "Simulated ethanol rises and levels off below the 130 g/L target, with a 120.4 g/L endpoint reference.",
    "F-0608 · On target": "Simulated ethanol rises and levels off above the 130 g/L target, with a 133.1 g/L endpoint reference.",
    "F-0609 · Recovery": "The simulated trend rises to a 131.3 g/L endpoint reference, clearing the target late in the replay.",
}
SELECTIONS = {SYNTHETIC: tuple(BATCHES), SPECTRAL: (PUBLIC_SEQUENCE,), SIMULATED_SPECTRA: (SPECTRAL_BATCH,)}


def synthetic_readings(scenario):
    return [Reading(row["Hour"] * HOUR, row["Hour"] * HOUR, row["Ethanol estimate"], scenario,
                    row["Temperature (°C)"], row["pH"]) for row in batch_readings(scenario)]


def spectral_readings(spectra, calibration, scenario):
    values = calibration.predict(spectra.drop(columns="_row", errors="ignore"))
    labels = spectra["_row"] if "_row" in spectra else spectra.index
    return [Reading(i * SPECTRAL_CADENCE, i * SPECTRAL_CADENCE, float(value), scenario, source_row=str(label))
            for i, (value, label) in enumerate(zip(values, labels, strict=True))]


def simulate_spectra(training_x, training_y):
    """Interpolate empirical signal templates in the original derivative representation."""
    rng = np.random.default_rng(SPECTRAL_SEED)
    order = np.argsort(training_y.to_numpy(), kind="stable")
    groups = np.array_split(order, 8)
    anchors = np.array([training_y.iloc[group].mean() for group in groups])
    templates = np.array([training_x.iloc[group].mean().to_numpy() for group in groups])
    minutes = np.arange(0, DISCHARGE + 1, SPECTRAL_CADENCE)
    fraction = minutes / DISCHARGE
    truth = anchors[0] + (anchors[-1] - anchors[0]) * (1 - (1 - fraction) ** 1.4)
    spectra = np.column_stack([np.interp(truth, anchors, template) for template in templates.T])
    spectra += rng.normal(size=spectra.shape) * training_x.std().to_numpy() * 0.005
    reference = float(truth[-1] + rng.normal(0, 0.4))
    return pd.DataFrame(spectra, columns=training_x.columns, index=minutes), truth, reference, anchors.tolist()


def precompute_forecasts(model, observations, discharge, cadence):
    if discharge is None:
        return []
    return issue_forecasts(model, observations, discharge, discharge, cadence)[0]
