CREATE TABLE IF NOT EXISTS model_runs (
    run_id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    target TEXT NOT NULL,
    snapshot_id TEXT REFERENCES dataset_versions(version_id),
    method TEXT NOT NULL,
    estimator_version TEXT NOT NULL,
    config_json TEXT NOT NULL CHECK (json_valid(config_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL CHECK (status IN ('pending', 'published'))
);
CREATE TABLE IF NOT EXISTS model_artifacts (
    run_id TEXT PRIMARY KEY REFERENCES model_runs(run_id),
    format TEXT NOT NULL,
    state_json TEXT NOT NULL CHECK (json_valid(state_json))
);
CREATE TABLE IF NOT EXISTS model_metrics (
    run_id TEXT NOT NULL REFERENCES model_runs(run_id),
    method TEXT NOT NULL,
    split TEXT NOT NULL,
    slice TEXT NOT NULL,
    sample_count INTEGER,
    metrics_json TEXT NOT NULL CHECK (json_valid(metrics_json)),
    PRIMARY KEY (run_id, method, split, slice)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS model_predictions (
    run_id TEXT NOT NULL REFERENCES model_runs(run_id),
    method TEXT NOT NULL,
    split TEXT NOT NULL,
    sample_key TEXT NOT NULL,
    issue_minute INTEGER NOT NULL,
    prediction REAL NOT NULL,
    reference REAL NOT NULL,
    label TEXT,
    features_json TEXT CHECK (features_json IS NULL OR json_valid(features_json)),
    PRIMARY KEY (run_id, method, split, sample_key, issue_minute)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS replay_batches (
    batch_version TEXT PRIMARY KEY,
    replay_mode TEXT NOT NULL,
    scenario TEXT NOT NULL,
    snapshot_id TEXT REFERENCES dataset_versions(version_id),
    calibration_run TEXT REFERENCES model_runs(run_id),
    forecast_run TEXT REFERENCES model_runs(run_id),
    cadence_minutes INTEGER NOT NULL,
    end_minute INTEGER NOT NULL,
    discharge_minute INTEGER,
    demo_target REAL,
    final_reference REAL,
    config_json TEXT NOT NULL CHECK (json_valid(config_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS replay_observations (
    batch_version TEXT NOT NULL REFERENCES replay_batches(batch_version),
    minute INTEGER NOT NULL,
    released_minute INTEGER NOT NULL,
    ethanol REAL NOT NULL,
    temperature REAL,
    ph REAL,
    source_version TEXT,
    source_split TEXT,
    source_position INTEGER,
    generated_spectrum_json TEXT CHECK (generated_spectrum_json IS NULL OR json_valid(generated_spectrum_json)),
    direct_ethanol REAL,
    PRIMARY KEY (batch_version, minute),
    FOREIGN KEY (source_version, source_split, source_position) REFERENCES spectral_inputs(version_id, split, position)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS replay_forecasts (
    batch_version TEXT NOT NULL REFERENCES replay_batches(batch_version),
    run_id TEXT NOT NULL REFERENCES model_runs(run_id),
    input_path TEXT NOT NULL,
    issue_minute INTEGER NOT NULL,
    lead_minutes INTEGER NOT NULL,
    availability TEXT NOT NULL,
    features_json TEXT NOT NULL CHECK (json_valid(features_json)),
    prediction REAL,
    PRIMARY KEY (batch_version, run_id, input_path, issue_minute)
) WITHOUT ROWID;
