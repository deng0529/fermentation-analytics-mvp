"""Explicit Turso migration and publication commands for saved model results."""

import argparse
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd
from sklearn import __version__ as sklearn_version

from example_data import BATCHES, TARGET
from fitted_state import FORMAT, SavedPredictor, calibration_state, ridge_state
from model_1a import VERIFIED_SNAPSHOT, fit_calibration, predict_calibration, reconstruct_demo
from model_2 import DISCHARGE, FEATURES, HOUR, MODEL_VERSION, SEED, train_model_2
from nir_calibration import compare_models, make_nir_split
from replay_data import (
    PUBLIC_SEQUENCE, SELECTIONS, SIMULATED_SPECTRA, SPECTRAL, SPECTRAL_BATCH, SPECTRAL_CADENCE,
    SPECTRAL_SEED, SPECTRAL_TARGET, SPECTRAL_VERSION, SYNTHETIC, precompute_forecasts,
    simulate_spectra, spectral_readings, synthetic_readings,
)
from results_store import TABLE_COLUMNS, all_rows, checked, encode, parity, publish, published, version_key
from spectral_store import NIR, load_versioned_dataset
from turso_database import DatasetError, connect, migrate


def add_run(bundle, name, model, method, snapshot, config, state):
    run = version_key(name)
    bundle["model_runs"].append((run, model, name if model == "Model 1A" else "Ethanol",
                                 snapshot, method, sklearn_version, encode(config), "pending"))
    bundle["model_artifacts"].append((run, FORMAT, encode(state)))
    return SavedPredictor(state)


def add_calibration(bundle, snapshot, target, spectra, references):
    pipeline = fit_calibration(snapshot, target, spectra, references)
    fitted = reconstruct_demo(snapshot, target, spectra, references, pipeline=pipeline)
    channels = spectra.drop(columns="_row")
    indexes = make_nir_split(channels.index)["display_indexes"]
    train, val, test = (list(indexes[name]) for name in ("Training", "Validation", "Test"))
    candidates = compare_models(channels, references[target], [(train, val)], 30, train,
                                channels.loc[test], references[target].loc[test])
    method = "PLS" if target == "Ethanol" else "SVR"
    display = {"settings": fitted["settings"], "intercept": fitted["intercept"], "max_error": fitted["max_error"]}
    tables = ("coefficients", "component_weights", "score_weights") if target == "Ethanol" else ("scaler",)
    display.update({name: fitted[name].to_dict("records") for name in tables})
    config = {"method": method, "display": display, "tables": tables, "seed": 42,
              "indexes": {"Training": train, "Validation": val, "Held-out test": test},
              "counts": {"Training": len(train), "Validation": len(val), "Held-out test": len(test)},
              "input_shape": channels.shape, "output_shape": (len(channels), 1), "candidate_count": len(candidates),
              "selection": {"PLS": "Validation MAE", "SVR": "Validation RMSE", "selected": fitted["settings"],
                            "policy": "Published Model 1A demonstration fit selected in the prior comparison."}}
    if target == "Glucose":
        config["support_positions"] = fitted["support"]["Source row position"].tolist()
    saved = add_run(bundle, target, "Model 1A", method, snapshot, config,
                    calibration_state(target, fitted, channels.columns))
    parity(saved.predict(channels), predict_calibration(pipeline, channels))
    run = version_key(target)
    for row in fitted["metrics"]:
        bundle["model_metrics"].append((run, method, row["Split"], "selected", row["Samples"], encode(row)))
    for index, candidate in enumerate(candidates):
        validation = candidate.get("validation", {})
        bundle["model_metrics"].append((run, candidate["method"], "Validation", f"candidate:{index:03}",
                                        validation.get("Samples"), encode(candidate)))
        if "test" in candidate:
            bundle["model_metrics"].append((run, candidate["method"], "Held-out test", f"candidate:{index:03}",
                                            candidate["test"]["Samples"], encode(candidate["test"])))
    for split, frame in fitted["evaluation"].items():
        for pos, label, measured, predicted in frame.itertuples(index=False, name=None):
            bundle["model_predictions"].append((run, method, split, str(pos), -1, predicted, measured, label, None))
    return saved


def add_ridge(bundle):
    pipeline, validation, test, metrics, sizes = train_model_2()
    state = ridge_state(pipeline)
    saved = add_run(bundle, "Ridge", "Model 2", "Ridge", None,
                    {"model_version": MODEL_VERSION, "features": FEATURES, "seed": SEED,
                     "sizes": sizes.to_dict("records"), "alpha": state["alpha"], "selection": "Validation MAE",
                     "discharge_minutes": DISCHARGE, "demo_target": TARGET}, state)
    parity(saved.predict(test[list(FEATURES)]), test["Ridge"])
    run = version_key("Ridge")
    validation_count = int(sizes.loc[sizes["Split"] == "Validation", "Windows"].item())
    for row in validation.to_dict("records"):
        bundle["model_metrics"].append((run, "Ridge", "Validation", f"alpha:{row['Alpha']:g}",
                                        validation_count, encode(row)))
    for row in metrics.to_dict("records"):
        bundle["model_metrics"].append((run, row["Method"], "Held-out test", f"lead:{row['Lead (h)']:02}",
                                        row["Samples"], encode(row)))
    for row in test.to_dict("records"):
        features = {name: row[name] for name in FEATURES}
        issue = int(DISCHARGE - features[FEATURES[-1]] * HOUR)
        for method in ("Ridge", "Trend baseline"):
            bundle["model_predictions"].append((run, method, "Held-out test", row["Batch"], issue, row[method],
                                                row["Reference (g/L)"], None, encode(features)))
    return saved


def add_replay(bundle, mode, scenario, readings, cadence, ridge=None, *, reference=None, target=None,
               generated=None, direct=None, config=None):
    version = version_key(scenario)
    spectral = mode in (SPECTRAL, SIMULATED_SPECTRA)
    snapshot = VERIFIED_SNAPSHOT if spectral else None
    calibration = version_key("Ethanol") if spectral else None
    ridge_run = version_key("Ridge") if ridge else None
    discharge = DISCHARGE if ridge else None
    bundle["replay_batches"].append((version, mode, scenario, snapshot, calibration, ridge_run, cadence,
                                     readings[-1].minute, discharge, target, reference, encode(config or {})))
    for index, row in enumerate(readings):
        public = mode == SPECTRAL
        bundle["replay_observations"].append((
            version, row.minute, row.released, row.ethanol, row.temperature, row.ph,
            snapshot if public else None, "calibration" if public else None, index if public else None,
            encode(generated.iloc[index].tolist()) if generated is not None else None,
            direct[index].ethanol if direct is not None else None,
        ))
    if ridge:
        paths = {"primary": readings}
        if direct is not None:
            paths["direct"] = direct
        for path, observations in paths.items():
            computed = precompute_forecasts(ridge, observations, discharge, cadence)
            checked(len(computed) == 34)
            for row in computed:
                issue = row["Issue minute"]
                bundle["replay_forecasts"].append((version, ridge_run, path, issue, discharge - issue,
                                                   "available", encode(row["features"]), row["Predicted ethanol (g/L)"]))


def build_bundle(snapshot, spectra, references):
    checked(snapshot == VERIFIED_SNAPSHOT)
    bundle = {table: [] for table in TABLE_COLUMNS}
    ethanol = add_calibration(bundle, snapshot, "Ethanol", spectra, references)
    add_calibration(bundle, snapshot, "Glucose", spectra, references)
    ridge = add_ridge(bundle)
    for scenario, (_, _, reference) in BATCHES.items():
        add_replay(bundle, SYNTHETIC, scenario, synthetic_readings(scenario), HOUR, ridge,
                   reference=reference, target=TARGET, config={"source": "example_data.py · fixed illustrative fixtures",
                   "target_source": "example_data.TARGET", "reference_source": "example_data.BATCHES third value",
                   "reference_release_minute": DISCHARGE})
    public = spectral_readings(spectra, ethanol, PUBLIC_SEQUENCE)
    add_replay(bundle, SPECTRAL, PUBLIC_SEQUENCE, public, SPECTRAL_CADENCE,
               config={"source": "chemometrics::NIR calibration", "clock": "simulated source order",
                       "schedule": "unknown"})
    features = spectra.drop(columns="_row")
    train = list(make_nir_split(features.index)["display_indexes"]["Training"])
    generated, true, reference, anchors = simulate_spectra(features.loc[train], references.loc[train, "Ethanol"])
    simulated = spectral_readings(generated, ethanol, SPECTRAL_BATCH)
    direct = [type(row)(row.minute, row.released, float(value), SPECTRAL_BATCH)
              for row, value in zip(simulated, true, strict=True)]
    direct_fit = fit_calibration(snapshot, "Ethanol", spectra, references)
    parity([row.ethanol for row in simulated], predict_calibration(direct_fit, generated))
    add_replay(bundle, SIMULATED_SPECTRA, SPECTRAL_BATCH, simulated, SPECTRAL_CADENCE, ridge,
               reference=reference, target=SPECTRAL_TARGET, generated=generated, direct=direct,
               config={"source": SPECTRAL_VERSION, "seed": SPECTRAL_SEED, "anchors": anchors,
                       "channels": features.columns.tolist(), "target_source": "replay_data.SPECTRAL_TARGET",
                       "reference_source": "Simulated terminal ethanol plus independent 0.4 g/L assay noise",
                       "reference_release_minute": DISCHARGE})
    return bundle


def print_counts(db):
    for table, columns in TABLE_COLUMNS.items():
        key = columns.split(",")[0]
        names = [scenario for choices in SELECTIONS.values() for scenario in choices] if key == "batch_version" else [
            "Ethanol", "Glucose", "Ridge"]
        count, = all_rows(db, f"SELECT COUNT(*) FROM {table} WHERE {key} IN ({','.join('?' for _ in names)})",
                          *(version_key(name) for name in names))
        print(f"{table}: {count[0]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("migrate", "backfill"))
    command = parser.parse_args().command
    secrets_path = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
    secrets = tomllib.loads(secrets_path.read_text(encoding="utf-8")) if secrets_path.exists() else {}
    try:
        db = connect(secrets)
        if command == "migrate":
            migrate(db)
            print("Turso migrations applied.")
            return
        if not published(db):
            snapshot, frames, _ = load_versioned_dataset(NIR, database=db)
            bundle = build_bundle(snapshot, *frames["calibration"])
            created = publish(db, bundle)
        else:
            created = False
        print("Published result bundle." if created else "Result bundle already published. No rows written.")
        print_counts(db)
    except DatasetError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
