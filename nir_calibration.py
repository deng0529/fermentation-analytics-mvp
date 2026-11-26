"""Validate and test spectral regressors on fixed, paired source rows."""

from random import Random
from warnings import catch_warnings, filterwarnings

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

NIR_SPLIT_SEED = 42
NIR_SPLIT_SIZES = {"Training": 116, "Validation": 25, "Test": 25}
CHEMOTOOLS_FOLD_COUNT = 5
CHEMOTOOLS_FOLD_SEED = 42
SVR_BASELINE = {"kernel": "rbf", "C": 10.0, "epsilon": 0.1, "gamma": 0.05}
SVR_C_VALUES = (0.1, 1.0, 10.0, 100.0, 1000.0)
SVR_GAMMA_MULTIPLIERS = (0.1, 1.0, 10.0)
SVR_SECOND_STAGE_EPSILONS = (0.01, 0.5, 1.0)


def make_nir_split(row_index):
    """Assign shared, one-based display indexes to the three partitions."""
    rows = list(row_index)
    if len(rows) != sum(NIR_SPLIT_SIZES.values()) or not row_index.is_unique:
        raise ValueError("The NIR split requires 166 unique paired rows.")
    Random(NIR_SPLIT_SEED).shuffle(rows)
    assignments = {}
    offset = 0
    for partition, count in NIR_SPLIT_SIZES.items():
        assignments[partition] = tuple(rows[offset:offset + count])
        offset += count
    return {"seed": NIR_SPLIT_SEED, "display_indexes": assignments}


def pls_component_limit(training):
    """Limit components to the rank of the centered training features."""
    values = training.to_numpy(dtype=float)
    return int(np.linalg.matrix_rank(values - values.mean(axis=0)))


def make_chemotools_folds(index):
    kfold = KFold(n_splits=CHEMOTOOLS_FOLD_COUNT, shuffle=True, random_state=CHEMOTOOLS_FOLD_SEED)
    return tuple((tuple(index[train]), tuple(index[validation])) for train, validation in kfold.split(index))


def fit_pls(components, train_x, train_y):
    with catch_warnings():
        filterwarnings("error", category=ConvergenceWarning)
        filterwarnings("error", message="y residual is constant.*", category=UserWarning)
        return PLSRegression(n_components=components, scale=True).fit(train_x, train_y)


def error_metrics(measured, predicted):
    measured, predicted = np.asarray(measured), np.asarray(predicted)
    if measured.shape != predicted.shape or not len(predicted) or not np.isfinite(predicted).all():
        raise ValueError("Evaluation requires matching, finite predictions.")
    error = predicted - measured
    return {
        "Samples": len(error),
        "MAE": float(np.abs(error).mean()),
        "RMSE": float(np.sqrt(np.square(error).mean())),
        "Bias": float(error.mean()),
    }


def compare_pls(features, reference, folds, default_maximum):
    """Score all PLS components using pooled validation predictions."""
    max_components = min(pls_component_limit(features.loc[list(train)]) for train, _ in folds)
    candidates = []
    for count in range(1, min(max_components, default_maximum) + 1):
        candidate = {"settings": {"n_components": count}}
        try:
            measured, predicted = [], []
            for train, validation in folds:
                train, validation = list(train), list(validation)
                model = fit_pls(count, features.loc[train], reference.loc[train])
                measured.extend(reference.loc[validation])
                predicted.extend(model.predict(features.loc[validation]).ravel())
            candidate["validation"] = error_metrics(measured, predicted)
        except (ValueError, FloatingPointError, np.linalg.LinAlgError, UserWarning) as error:
            candidate["failure"] = str(error)
        candidates.append(candidate)
    return candidates


def scaled_training(features):
    scaler = StandardScaler().set_output(transform="pandas")
    training = scaler.fit_transform(features)
    variance = float(training.to_numpy().var())
    scale_gamma = 1.0 / (training.shape[1] * variance) if variance else 1.0
    return scaler, training, scale_gamma


def fit_svr(settings, training, reference, scale_gamma):
    gamma = settings["gamma"] if "gamma" in settings else settings["gamma_multiplier"] * scale_gamma
    parameters = {"kernel": "rbf", "C": settings["C"], "epsilon": settings["epsilon"], "gamma": gamma}
    with catch_warnings():
        filterwarnings("error", category=ConvergenceWarning)
        model = SVR(**parameters).fit(training, reference)
    return model, gamma


def compare_svr(features, reference, folds):
    """Reuse the two-stage RBF search on one hold-out split or pooled out-of-fold predictions."""
    fold_data = []
    for train, validation in folds:
        train, validation = list(train), list(validation)
        scaler, train_x, scale_gamma = scaled_training(features.loc[train])
        fold_data.append((train_x, reference.loc[train], scaler.transform(features.loc[validation]),
                          reference.loc[validation], scale_gamma))
    candidates = {}

    def evaluate(settings):
        gammas = tuple(
            settings["gamma"] if "gamma" in settings else settings["gamma_multiplier"] * fold[-1]
            for fold in fold_data
        )
        key = settings["C"], gammas, settings["epsilon"]
        if key not in candidates:
            row = {"settings": settings, "validation_gammas": gammas}
            candidates[key] = row
            try:
                measured, predicted = [], []
                for train_x, train_y, val_x, val_y, scale_gamma in fold_data:
                    model, _ = fit_svr(settings, train_x, train_y, scale_gamma)
                    measured.extend(val_y)
                    predicted.extend(model.predict(val_x))
                row["validation"] = error_metrics(measured, predicted)
            except (ValueError, FloatingPointError, ConvergenceWarning) as error:
                row["failure"] = str(error)
        return candidates[key]

    first_stage = [
        evaluate({"kernel": "rbf", "C": c, "gamma_multiplier": multiplier, "epsilon": 0.1})
        for c in SVR_C_VALUES for multiplier in SVR_GAMMA_MULTIPLIERS
    ]
    successful = [row for row in first_stage if "validation" in row]
    for row in sorted(successful, key=lambda row: row["validation"]["RMSE"])[:3]:
        for epsilon in SVR_SECOND_STAGE_EPSILONS:
            evaluate({**row["settings"], "epsilon": epsilon})
    evaluate(SVR_BASELINE)
    return list(candidates.values())


def compare_models(features, reference, folds, default_maximum, final_train, test_features, test_reference, matches=None):
    """Select both winners before predicting either test set."""
    if not features.index.equals(reference.index):
        raise ValueError("Calibration spectra and reference values must share row indexes.")
    searches = (
        ("PLS", compare_pls(features, reference, folds, default_maximum), "MAE"),
        ("SVR", compare_svr(features, reference, folds), "RMSE"),
    )
    winners, remaining = [], []
    for method, candidates, criterion in searches:
        candidates.sort(key=lambda row: row.get("validation", {}).get(criterion, float("inf")))
        winner = next((candidate for candidate in candidates if "validation" in candidate), None)
        for candidate in candidates:
            candidate["method"] = method
            candidate["winner"] = candidate is winner
            (winners if candidate is winner else remaining).append(candidate)

    train_x, train_y = features.loc[list(final_train)], reference.loc[list(final_train)]
    if matches is not None and matches.empty:
        raise ValueError("The stored approximate alignment has no matched HPLC records.")
    for winner in winners:
        settings = winner["settings"]
        if winner["method"] == "PLS":
            model = fit_pls(settings["n_components"], train_x, train_y)
            predictions = model.predict(test_features).ravel()
        else:
            scaler, training, scale_gamma = scaled_training(train_x)
            model, gamma = fit_svr(settings, training, train_y, scale_gamma)
            winner["test_gamma"] = gamma
            predictions = model.predict(scaler.transform(test_features))
        if matches is not None:
            predictions = predictions[matches["spectrum_position"].to_numpy(dtype=int)]
        winner["test"] = error_metrics(test_reference, predictions)
    return winners + remaining
