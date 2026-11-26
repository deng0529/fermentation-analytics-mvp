"""Portable inference equations for published runs. No estimator deserialization."""

import numpy as np

FORMAT = "equations-json-v1"


class SavedPredictor:
    def __init__(self, state):
        self.state = state
        self.feature_names_in_ = tuple(state["features"])

    def predict(self, frame):
        if tuple(frame.columns) != self.feature_names_in_:
            raise ValueError("Input feature names or order differ from the saved fit.")
        state = self.state
        x = frame.to_numpy(dtype=float)
        if state["kind"] in ("ridge", "rbf"):
            x = (x - np.asarray(state["mean"])) / np.asarray(state["scale"])
        if state["kind"] in ("pls", "ridge"):
            return state["intercept"] + x @ np.asarray(state["weights"])
        if state["kind"] == "rbf":
            support = np.asarray(state["support"])
            weights = np.asarray(state["weights"])
            return np.concatenate([
                state["intercept"] + np.exp(-state["gamma"] * np.square(
                    x[start:start + 64, None, :] - support[None, :, :]
                ).sum(axis=2)) @ weights
                for start in range(0, len(x), 64)
            ])
        raise ValueError("Unknown fitted equation.")


def calibration_state(target, fitted, channels):
    state = {"features": list(channels), "intercept": fitted["intercept"]}
    if target == "Ethanol":
        return {**state, "kind": "pls", "weights": fitted["coefficients"]["Coefficient"].tolist()}
    support, scaler = fitted["support"], fitted["scaler"]
    return {**state, "kind": "rbf", "mean": scaler["Mean"].tolist(), "scale": scaler["Scale"].tolist(),
            "weights": support["Signed dual coefficient"].tolist(), "support": support[list(channels)].to_numpy().tolist(),
            "gamma": fitted["settings"]["gamma"]}


def ridge_state(pipeline):
    scaler, ridge = pipeline
    return {"kind": "ridge", "features": pipeline.feature_names_in_.tolist(), "mean": scaler.mean_.tolist(),
            "scale": scaler.scale_.tolist(), "weights": ridge.coef_.tolist(), "intercept": float(ridge.intercept_),
            "alpha": float(ridge.alpha)}
