"""Read, verify, and atomically publish the versioned Turso result bundle."""

import json
from hashlib import sha256

import numpy as np
import pandas as pd
from sklearn import __version__ as sklearn_version

from fitted_state import FORMAT, SavedPredictor
from model_1a import VERIFIED_SNAPSHOT
from model_2 import FEATURES, HOUR, Reading
from nir_calibration import error_metrics
from replay_data import SIMULATED_SPECTRA, SPECTRAL, SPECTRAL_CADENCE, precompute_forecasts
from spectral_store import insert_rows
from turso_database import DatasetError

RELEASE = "replay-results-v1"
RECOVERY = ("Saved results are missing or incomplete. Run python backfill_results.py migrate and "
            "python backfill_results.py backfill. If the release is already published, restore its complete "
            "data or publish a corrected version.")
TABLE_COLUMNS = {
    "model_runs": "run_id,model,target,snapshot_id,method,estimator_version,config_json,status",
    "model_artifacts": "run_id,format,state_json",
    "model_metrics": "run_id,method,split,slice,sample_count,metrics_json",
    "model_predictions": "run_id,method,split,sample_key,issue_minute,prediction,reference,label,features_json",
    "replay_batches": "batch_version,replay_mode,scenario,snapshot_id,calibration_run,forecast_run,cadence_minutes,"
                      "end_minute,discharge_minute,demo_target,final_reference,config_json",
    "replay_observations": "batch_version,minute,released_minute,ethanol,temperature,ph,source_version,source_split,"
                           "source_position,generated_spectrum_json,direct_ethanol",
    "replay_forecasts": "batch_version,run_id,input_path,issue_minute,lead_minutes,availability,features_json,prediction",
}


def encode(value):
    return json.dumps(value, allow_nan=False, separators=(",", ":"))


def version_key(name):
    return sha256(encode((RELEASE, VERIFIED_SNAPSHOT, sklearn_version, name)).encode()).hexdigest()


def all_rows(db, sql, *args):
    return db.execute((sql, args))[0]


def checked(condition):
    if not condition:
        raise DatasetError(RECOVERY)


def parity(actual, expected):
    if not np.allclose(actual, expected, rtol=0, atol=1e-9):
        raise DatasetError("Saved results failed inference parity. Rebuild a corrected result version.")


def published(db):
    rows = all_rows(db, "SELECT status FROM model_runs WHERE run_id IN (?,?,?)",
                    *(version_key(name) for name in ("Ethanol", "Glucose", "Ridge")))
    return len(rows) == 3 and all(status == "published" for status, in rows)


def publish(db, bundle):
    with db.session() as session:
        session.execute(("PRAGMA foreign_keys = ON", ()), ("BEGIN IMMEDIATE", ()))
        existing, = session.execute(("SELECT 1 FROM model_runs WHERE run_id=?", (version_key("Ridge"),)))
        if existing:
            session.execute(("ROLLBACK", ()), close=True)
            return False
        for table, columns in TABLE_COLUMNS.items():
            chunk = 24 if table == "replay_observations" else 96
            insert_rows(session, table, columns, bundle[table], len(columns.split(",")), chunk)
            keys = tuple(row[0] for row in bundle[table]) if table in ("model_runs", "replay_batches") else ()
            if keys:
                count, = session.execute((f"SELECT COUNT(*) FROM {table} WHERE {columns.split(',')[0]} "
                                          f"IN ({','.join('?' for _ in keys)})", keys))
                checked(count == [(len(keys),)])
        for table, parents in (("model_artifacts", "model_runs"), ("model_predictions", "model_runs"),
                               ("model_metrics", "model_runs"), ("replay_observations", "replay_batches"),
                               ("replay_forecasts", "replay_batches")):
            keys = tuple(row[0] for row in bundle[parents])
            column = TABLE_COLUMNS[table].split(",")[0]
            counts, = session.execute((f"SELECT COUNT(*) FROM {table} WHERE {column} "
                                       f"IN ({','.join('?' for _ in keys)})", keys))
            checked(counts == [(len(bundle[table]),)])
        session.execute(("UPDATE model_runs SET status='published' WHERE run_id IN (?,?,?)",
                         tuple(row[0] for row in bundle["model_runs"])), ("COMMIT", ()), close=True)
    return True


def load_run(db, name):
    run = version_key(name)
    rows = all_rows(db, "SELECT r.config_json,a.format,a.state_json FROM model_runs r "
                    "JOIN model_artifacts a USING(run_id) WHERE r.run_id=? AND r.status='published'", run)
    checked(len(rows) == 1 and rows[0][1] == FORMAT)
    config, _, state = rows[0]
    return run, json.loads(config), SavedPredictor(json.loads(state))


def evaluation_rows(db, run, split, method=None, issues=None):
    sql = ("SELECT method,sample_key,issue_minute,prediction,reference,label,features_json FROM model_predictions "
           "WHERE run_id=? AND split=?")
    args = [run, split]
    if method:
        sql += " AND method=?"
        args.append(method)
    if issues:
        sql += f" AND issue_minute IN ({','.join('?' for _ in issues)})"
        args.extend(issues)
    return all_rows(db, sql + " ORDER BY issue_minute, sample_key, method", *args)


def load_calibration(db, target, features):
    run, config, predictor = load_run(db, target)
    method = config["method"]
    metrics = []
    frames = {}
    for split in ("Validation", "Held-out test"):
        rows = evaluation_rows(db, run, split, method)
        checked(len(rows) == config["counts"][split])
        frame = pd.DataFrame([{"Source row position": int(key), "Source row label": label,
                               "Measured": y, "Predicted": p} for _, key, _, p, y, label, _ in rows])
        frame = frame.set_index("Source row position").loc[config["indexes"][split]].reset_index()
        parity(predictor.predict(features.loc[frame["Source row position"]]), frame["Predicted"])
        saved = all_rows(db, "SELECT metrics_json FROM model_metrics WHERE run_id=? AND method=? AND split=? "
                         "AND slice='selected'", run, method, split)
        checked(len(saved) == 1)
        stats = json.loads(saved[0][0])
        actual = error_metrics(frame["Measured"], frame["Predicted"])
        parity(list(actual.values()), [stats[k] for k in actual])
        metrics.append({"Split": split, **stats})
        frames[split] = frame
    detail = config["display"].copy()
    for name in config["tables"]:
        detail[name] = pd.DataFrame(detail[name])
    state = predictor.state
    if target == "Glucose":
        support = pd.DataFrame(state["support"], columns=state["features"])
        support.insert(0, "Signed dual coefficient", state["weights"])
        support.insert(0, "Source row position", config["support_positions"])
        detail["support"] = support
    candidates = [json.loads(row[0]) for row in all_rows(
        db, "SELECT metrics_json FROM model_metrics WHERE run_id=? AND split='Validation' "
        "AND slice LIKE 'candidate:%' ORDER BY slice", run)]
    checked(len(candidates) == config["candidate_count"])
    return {**detail, "metrics": metrics, "predictions": frames["Held-out test"],
            "predictor": predictor, "run": run, "config": config, "candidates": candidates}


def load_ridge(db):
    run, config, predictor = load_run(db, "Ridge")
    checked(tuple(predictor.feature_names_in_) == FEATURES)
    rows = all_rows(db, "SELECT method,split,slice,metrics_json FROM model_metrics WHERE run_id=? "
                    "ORDER BY split,slice,method", run)
    validation = pd.DataFrame([json.loads(payload) for _, split, _, payload in rows if split == "Validation"])
    metrics = pd.DataFrame([json.loads(payload) for _, split, _, payload in rows if split == "Held-out test"])
    validation = validation.sort_values("Alpha").reset_index(drop=True)
    metrics = metrics.sort_values(["Lead (h)", "Method"], ascending=[False, True]).reset_index(drop=True)
    issues = [(36 - lead) * HOUR for lead in (12, 6, 2)]
    records = evaluation_rows(db, run, "Held-out test", issues=issues)
    checked(len(records) == 480 and len(metrics) == 6 and len(validation) == 5)
    test = pd.DataFrame([{"Batch": key, "Reference (g/L)": y, "Method": method, "Predicted": p, **json.loads(x)}
                         for method, key, _, p, y, _, x in records])
    ridge = test[test["Method"] == "Ridge"]
    parity(predictor.predict(ridge[list(FEATURES)]), ridge["Predicted"])
    baseline = test[test["Method"] == "Trend baseline"]
    latest, slope, remaining = FEATURES
    parity(baseline[latest] + baseline[slope] * baseline[remaining], baseline["Predicted"])
    for row in metrics.to_dict("records"):
        selected = test[(test[FEATURES[-1]] == row["Lead (h)"]) & (test["Method"] == row["Method"])]
        actual = error_metrics(selected["Reference (g/L)"], selected["Predicted"])
        parity(list(actual.values()), [row[name] if name == "Samples" else row[f"{name} (g/L)"] for name in actual])
        parity(actual["RMSE"] ** 2, row["MSE ((g/L)²)"])
        below = selected["Reference (g/L)"] < config["demo_target"]
        warning = selected["Predicted"] < config["demo_target"]
        checked([int(below.sum()), int((~below).sum()), int((below & ~warning).sum()),
                 int((~below & warning).sum())] ==
                [row["Actual shortfalls"], row["Actual at or above target"], row["Missed shortfalls"],
                 row["False warnings"]])
    test = test.pivot(index=["Batch", "Reference (g/L)", *FEATURES], columns="Method", values="Predicted").reset_index()
    return predictor.state, validation, test, metrics, pd.DataFrame(config["sizes"])


def load_replay(db, scenario, spectra_loader):
    version = version_key(scenario)
    rows = all_rows(db, "SELECT replay_mode,cadence_minutes,end_minute,discharge_minute,demo_target,final_reference,"
                    "config_json,calibration_run,forecast_run FROM replay_batches WHERE batch_version=?", version)
    checked(len(rows) == 1)
    mode, cadence, end, discharge, target, ref, config, cal_run, ridge_run = rows[0]
    config = json.loads(config)
    projection = ("minute,released_minute,ethanol,temperature,ph,source_position,direct_ethanol,"
                  "generated_spectrum_json")
    pages = [(f"SELECT {projection} FROM replay_observations WHERE batch_version=? AND minute BETWEEN ? AND ? "
              "ORDER BY minute", (version, start, start + 63 * cadence))
             for start in range(0, end + 1, 64 * cadence)]
    observations = [row for page in db.execute(*pages) for row in page]
    checked([row[0] for row in observations] == list(range(0, end + 1, cadence)))
    labels = [str(row[0]) for row in observations]
    if cal_run:
        run, _, calibration = load_run(db, "Ethanol")
        checked(run == cal_run)
        if mode == SPECTRAL:
            snapshot, frames, _ = spectra_loader()
            checked(snapshot == VERIFIED_SNAPSHOT and [r[5] for r in observations] == list(range(len(observations))))
            spectra = frames["calibration"][0]
            labels = spectra["_row"].tolist()
            features = spectra.drop(columns="_row")
        else:
            checked(mode == SIMULATED_SPECTRA and all(row[-1] is not None for row in observations))
            checked(tuple(config["channels"]) == calibration.feature_names_in_)
            features = pd.DataFrame([json.loads(row[-1]) for row in observations], columns=calibration.feature_names_in_)
        parity(calibration.predict(features), [row[2] for row in observations])
    readings = [Reading(row[0], row[1], row[2], scenario, row[3], row[4], label)
                for row, label in zip(observations, labels, strict=True)]
    forecast_rows = all_rows(db, "SELECT input_path,issue_minute,lead_minutes,features_json,prediction "
                             "FROM replay_forecasts WHERE batch_version=? AND run_id=? AND availability='available' "
                             "ORDER BY issue_minute", version, ridge_run)
    forecasts = {}
    if ridge_run:
        run, _, model = load_run(db, "Ridge")
        checked(run == ridge_run)
        paths = {"primary": readings}
        if mode == SIMULATED_SPECTRA:
            paths["direct"] = [Reading(row[0], row[1], row[6], scenario) for row in observations]
        for path, inputs in paths.items():
            saved = [{"Issue minute": issue, "Predicted ethanol (g/L)": p, "features": json.loads(features)}
                     for name, issue, lead, features, p in forecast_rows if name == path and lead == discharge - issue]
            recomputed = precompute_forecasts(model, inputs, discharge, cadence)
            checked(len(saved) == len(recomputed) == 34)
            for before, after in zip(saved, recomputed, strict=True):
                checked(before["Issue minute"] == after["Issue minute"])
                parity([before["features"][key] for key in FEATURES], list(after["features"].values()))
                parity(before["Predicted ethanol (g/L)"], after["Predicted ethanol (g/L)"])
            forecasts[path] = saved
    return {"mode": mode, "scenario": scenario, "end": end, "cadence": cadence, "discharge": discharge,
            "target": target, "reference": ref, "readings": readings, "forecasts": forecasts, "config": config,
            "version": version}
