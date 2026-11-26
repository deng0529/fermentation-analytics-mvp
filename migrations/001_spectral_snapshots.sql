CREATE TABLE IF NOT EXISTS dataset_versions (
    version_id TEXT PRIMARY KEY,
    dataset TEXT NOT NULL UNIQUE,
    source_uri TEXT NOT NULL,
    package_version TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    schema_json TEXT NOT NULL CHECK (json_valid(schema_json))
);

CREATE TABLE IF NOT EXISTS spectral_inputs (
    version_id TEXT NOT NULL REFERENCES dataset_versions(version_id),
    split TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    source_index INTEGER NOT NULL,
    source_row_label TEXT,
    readings_json TEXT NOT NULL CHECK (json_valid(readings_json)),
    PRIMARY KEY (version_id, split, position),
    UNIQUE (version_id, split, source_index)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS reference_outputs (
    version_id TEXT NOT NULL REFERENCES dataset_versions(version_id),
    split TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    source_index INTEGER NOT NULL,
    values_json TEXT NOT NULL CHECK (json_valid(values_json)),
    PRIMARY KEY (version_id, split, position),
    UNIQUE (version_id, split, source_index)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS test_alignment (
    version_id TEXT NOT NULL,
    split TEXT NOT NULL CHECK (split = 'test'),
    spectrum_position INTEGER NOT NULL,
    reference_position INTEGER NOT NULL,
    estimated_spectrum_hour REAL NOT NULL,
    recorded_hplc_hour REAL NOT NULL,
    matching_rule TEXT NOT NULL,
    approximate INTEGER NOT NULL CHECK (approximate = 1),
    PRIMARY KEY (version_id, split, reference_position),
    FOREIGN KEY (version_id, split, spectrum_position) REFERENCES spectral_inputs(version_id, split, position),
    FOREIGN KEY (version_id, split, reference_position) REFERENCES reference_outputs(version_id, split, position)
) WITHOUT ROWID;
