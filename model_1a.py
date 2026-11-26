"""Reconstruct the two fitted Model 1A demo equations from the verified snapshot."""

import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline

from nir_calibration import error_metrics, fit_pls, fit_svr, make_nir_split, scaled_training

VERIFIED_SNAPSHOT = "f0e482970f5c538ca87bd8ae8c35017a5f43d08b0ff367437b5f131940eaa9dd"
ETHANOL_COMPONENTS = 10
GLUCOSE_SETTINGS = {"kernel": "rbf", "C": 1000.0, "gamma_multiplier": 1.0, "epsilon": 0.01}
EQUATION_ATOL = 1e-9


def fit_calibration(version_id, target, spectra, references):
    if version_id != VERIFIED_SNAPSHOT:
        raise ValueError("The active NIR snapshot differs from the verified Model 1A snapshot.")
    features = spectra.drop(columns="_row")
    if features.shape != (166, 235) or not features.index.equals(references.index):
        raise ValueError("Model 1A requires the 166 paired samples and their 235 source spectral channels.")
    reference = references[target]
    indexes = make_nir_split(features.index)["display_indexes"]
    train = list(indexes["Training"])
    train_x, train_y = features.loc[train], reference.loc[train]
    if target == "Ethanol":
        pipeline = fit_pls(ETHANOL_COMPONENTS, train_x, train_y)
    elif target == "Glucose":
        scaler, scaled_train, scale_gamma = scaled_training(train_x)
        model, _ = fit_svr(GLUCOSE_SETTINGS, scaled_train, train_y, scale_gamma)
        pipeline = make_pipeline(scaler, model)
    else:
        raise ValueError("Unknown Model 1A target.")
    return pipeline


def predict_calibration(pipeline, features):
    if not np.array_equal(features.columns, pipeline.feature_names_in_):
        raise ValueError("Spectral channels must match the calibration names and source order.")
    return pipeline.predict(features).ravel()


def reconstruct_demo(version_id, target, spectra, references, *, pipeline=None):
    if pipeline is None:
        pipeline = fit_calibration(version_id, target, spectra, references)
    features = spectra.drop(columns="_row")
    reference = references[target]
    indexes = make_nir_split(features.index)["display_indexes"]
    train, validation, test = (list(indexes[name]) for name in ("Training", "Validation", "Test"))
    train_y = reference.loc[train]
    validation_x, test_x = features.loc[validation], features.loc[test]
    validation_predictions = predict_calibration(pipeline, validation_x)
    test_predictions = predict_calibration(pipeline, test_x)
    wavelengths = pd.DataFrame({
        "Channel": features.columns,
        "Wavelength (nm)": [float(label[1:]) for label in features.columns],
    })

    if target == "Ethanol":
        model = pipeline
        coefficients = model.coef_.ravel()
        origin = pd.DataFrame([np.zeros(features.shape[1])], columns=features.columns)
        intercept = float(model.predict(origin).item())
        equation_predictions = intercept + test_x.to_numpy() @ coefficients
        component_labels = [f"Component {i + 1}" for i in range(model.n_components)]
        score_weights = model.y_loadings_.ravel() * train_y.std(ddof=1)
        detail = {
            "intercept": intercept, "coefficients": wavelengths.assign(Coefficient=coefficients),
            "component_weights": wavelengths.join(pd.DataFrame(model.x_weights_, columns=component_labels)),
            "score_weights": pd.DataFrame({"Component": component_labels, "Regression weight (g/L)": score_weights}),
            "settings": {"n_components": model.n_components, "scale": model.scale},
        }
    elif target == "Glucose":
        scaler, model = pipeline[0], pipeline[1]
        gamma = model.gamma
        intercept = float(model.intercept_.item())
        weights = model.dual_coef_.ravel()
        # Evaluate the exported rule from original spectra using the exported scaling parameters.
        coordinates = (test_x.to_numpy() - scaler.mean_) / scaler.scale_
        squared_distances = np.square(coordinates[:, None, :] - model.support_vectors_[None, :, :]).sum(axis=2)
        equation_predictions = intercept + np.exp(-gamma * squared_distances) @ weights
        support = pd.DataFrame(model.support_vectors_, columns=features.columns)
        support.insert(0, "Signed dual coefficient", weights)
        support.insert(0, "Source row position", features.loc[train].index[model.support_])
        detail = {
            "intercept": intercept, "settings": {name: model.get_params()[name]
                                                 for name in ("kernel", "C", "gamma", "epsilon")},
            "support": support,
            "scaler": wavelengths.assign(Mean=scaler.mean_, Scale=scaler.scale_),
        }

    max_error = float(np.max(np.abs(equation_predictions - test_predictions)))
    if max_error > EQUATION_ATOL or not np.isfinite(max_error):
        raise ValueError("The exported Model 1A equation did not reproduce the estimator’s held-out predictions.")
    metrics = [
        {"Split": label, **error_metrics(reference.loc[rows], predictions)}
        for label, rows, predictions in (
            ("Validation", validation, validation_predictions), ("Held-out test", test, test_predictions),
        )
    ]
    evaluation = {
        label: pd.DataFrame({
            "Source row position": rows, "Source row label": spectra.loc[rows, "_row"].to_list(),
            "Measured": reference.loc[rows].to_numpy(), "Predicted": predictions,
        })
        for label, rows, predictions in (
            ("Validation", validation, validation_predictions), ("Held-out test", test, test_predictions),
        )
    }
    return {**detail, "max_error": max_error, "metrics": metrics,
            "predictions": evaluation["Held-out test"], "evaluation": evaluation}
