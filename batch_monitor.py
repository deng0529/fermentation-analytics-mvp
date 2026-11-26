"""Streamlit operator replay and Model 2 validation views."""

import altair as alt
import pandas as pd
import streamlit as st

from data_provenance import show_replay_source

from model_2 import FEATURES, HOUR, SEED
from replay_data import SELECTIONS, SCENARIOS, SIMULATED_SPECTRA, SPECTRAL, SYNTHETIC
from results_store import RECOVERY, RELEASE, load_calibration, load_replay, load_ridge
from turso_database import DatasetError

CLOCK_KEY = "batch_replay_minute"
PLAYING_KEY = "batch_replay_playing"
MODE_COPY = {
    SYNTHETIC: "This replay feeds simulated ethanol readings directly to the saved Ridge model. "
               "The three example trajectories have simulated discharge references. Held-out error is measured on separate synthetic batches.",
    SPECTRAL: "This replay applies the saved ethanol PLS calibration to public NIR source rows on a simulated clock. "
              "It demonstrates current ethanol estimation. A discharge forecast requires a timestamped batch history and a scheduled discharge.",
    SIMULATED_SPECTRA: "This replay feeds illustrative spectra through the saved ethanol PLS calibration and then Ridge. "
                       "The same simulated trajectory also supplies a direct-input comparison. Results describe one example batch.",
}


@st.cache_data(ttl=300, show_spinner=False)
def saved_ridge(release, _database):
    return load_ridge(_database())


@st.cache_data(ttl=300, show_spinner=False)
def saved_replay(release, scenario, _database, _spectra):
    return load_replay(_database(), scenario, _spectra)


@st.cache_data(ttl=300, show_spinner=False)
def saved_ethanol_evaluation(release, _database, _spectra):
    _, frames, _ = _spectra()
    return load_calibration(_database(), "Ethanol", frames["calibration"][0].drop(columns="_row"))


def set_clock(minute=0):
    pause()
    st.session_state[CLOCK_KEY] = minute


def pause():
    st.session_state[PLAYING_KEY] = False


def toggle_playback():
    st.session_state[PLAYING_KEY] = not st.session_state.get(PLAYING_KEY, False)


def clock_label(minute):
    hours, minutes = divmod(minute, HOUR)
    return f"{hours} h {minutes:02d} min" if minutes else f"{hours} h"


def show_batch(database, load_snapshot):
    st.title("Batch Monitor")
    try:
        details = saved_ridge(RELEASE, database)
    except (DatasetError, ValueError, KeyError) as error:
        st.error(f"{error} {RECOVERY}")
        return
    playing = st.session_state.get(PLAYING_KEY, False)
    initial_render = True

    @st.fragment(run_every=1 if playing else None)
    def operator():
        nonlocal initial_render
        if st.session_state.get(PLAYING_KEY, False) != playing:
            st.rerun()
        tick = playing and not initial_render
        initial_render = False
        show_operator(database, load_snapshot, details[3], playing, tick)

    operator()
    show_model_2_details(*details)


def show_operator(database, load_snapshot, metrics, playing, tick):
    with st.container(border=True, key="panel-replay"):
        mode = st.selectbox("Replay source", tuple(SELECTIONS), key="batch_replay_source", on_change=set_clock)
        scenario = st.selectbox("Replay sequence" if mode == SPECTRAL else "Batch", SELECTIONS[mode],
                                key=f"batch_replay_selection_{mode}", on_change=set_clock)
        st.write(MODE_COPY[mode])
        if scenario in SCENARIOS:
            st.caption(SCENARIOS[scenario])
        try:
            with st.spinner("Loading saved replay observations and results…", show_time=False):
                replay = saved_replay(RELEASE, scenario, database, load_snapshot)
        except (DatasetError, ValueError, KeyError) as error:
            if playing:
                pause()
                st.rerun()
            st.error(f"{error} {RECOVERY}")
            return
        end, cadence, discharge = replay["end"], replay["cadence"], replay["discharge"]
        st.session_state.setdefault(CLOCK_KEY, 0)
        now = st.session_state[CLOCK_KEY]
        if tick:
            now = min(end, now + HOUR)
            st.session_state[CLOCK_KEY] = now
            if now == end:
                pause()
                st.rerun()
        timing = st.columns(3)
        timing[0].metric("Simulated elapsed time" if mode == SPECTRAL else "Elapsed time", clock_label(now))
        timing[1].metric("Scheduled discharge", "Unknown" if discharge is None else clock_label(discharge))
        timing[2].metric("Replay duration" if discharge is None else "Time remaining",
                         clock_label(end if discharge is None else discharge - now))
        with st.container(horizontal=True):
            st.button("Pause" if playing else "Play", key="batch_play_pause", disabled=now == end,
                      on_click=toggle_playback)
            st.button("Restart replay", on_click=set_clock)
            st.button("Previous hour", disabled=now == 0, on_click=set_clock, args=(max(0, now - HOUR),))
            st.button("Next hour", disabled=now == end, on_click=set_clock, args=(min(end, now + HOUR),))
        now = st.slider("Elapsed time (minutes)", 0, end, step=cadence, key=CLOCK_KEY, on_change=pause)

    readings = [row for row in replay["readings"] if row.minute <= now and row.released <= now]
    forecasts = [row for row in replay["forecasts"].get("primary", []) if row["Issue minute"] <= now]
    lab = replay["reference"] if now >= replay["config"].get("reference_release_minute", end) else None
    if discharge is not None:
        show_forecast(forecasts, now, discharge, mode, replay["target"])
    show_readings(readings, forecasts, now, end, mode, lab)
    show_accuracy(database, load_snapshot, replay, metrics, now, lab)
    show_replay_source(mode)


def show_forecast(forecasts, now, discharge, mode, target):
    with st.container(border=True, key="panel-forecast"):
        st.subheader("Discharge forecast")
        if mode == SIMULATED_SPECTRA:
            st.caption("Simulation only · illustrative spectra and simulated discharge")
        latest = forecasts[-1] if forecasts else None
        predicted = latest["Predicted ethanol (g/L)"] if latest else None
        gap = predicted - target if latest else None
        cards = st.columns(4)
        cards[0].metric("Predicted ethanol", f"{predicted:.1f} g/L" if latest else "—")
        cards[1].metric("Demo target", f"{target:.0f} g/L")
        cards[2].metric("Distance from target" if mode == SIMULATED_SPECTRA else "Difference from target",
                        f"{gap:+.1f} g/L" if latest else "—")
        cards[3].metric("Forecast issue time", clock_label(latest["Issue minute"]) if latest else "—")
        if now == 30 * HOUR:
            st.caption("Hour 30 · six-hour checkpoint")
        if not latest:
            st.info("Waiting for two hours of usable ethanol history.")
        if now >= discharge:
            st.caption("Discharge reached. The card retains the most recent pre-discharge forecast.")
        if latest and mode == SYNTHETIC and now < discharge:
            if gap < 0:
                st.warning(f"Potential shortfall at discharge · {-gap:.1f} g/L below target.")
            else:
                st.success("Forecast meets the demo target.")


def show_readings(readings, forecasts, now, discharge, mode, lab):
    spectral = mode != SYNTHETIC
    with st.container(border=True, key="panel-current"):
        st.subheader("Current Model 1 ethanol estimate" if spectral else "Current simulated ethanol reading")
        if readings:
            latest = readings[-1]
            st.metric("Current ethanol estimate", f"{latest.ethanol:.1f} g/L")
            st.caption(f"Latest reading at {clock_label(latest.minute)} · {latest.source}")
            if spectral:
                st.caption("Model 1 ethanol uses the fitted, scaled 10-component PLS calibration.")
        else:
            st.info("No ethanol readings are available.")

    trend_label = "Model 1 ethanol estimates" if spectral else "Simulated ethanol readings"
    st.subheader(trend_label)
    if readings:
        trend = pd.DataFrame({"Elapsed hour": [row.minute / HOUR for row in readings],
                              "Ethanol (g/L)": [row.ethanol for row in readings]})
        line = alt.Chart(trend).mark_line(point=True).encode(
            x=alt.X("Elapsed hour:Q", scale=alt.Scale(domain=[0, discharge / HOUR])),
            y=alt.Y("Ethanol (g/L):Q"), tooltip=["Elapsed hour:Q", alt.Tooltip("Ethanol (g/L):Q", format=".2f")],
        )
        if lab is not None and now >= discharge:
            reference = pd.DataFrame({"Elapsed hour": [discharge / HOUR], "Ethanol (g/L)": [lab]})
            line += alt.Chart(reference).mark_point(shape="diamond", filled=True, color="#9c4700", size=110).encode(
                x="Elapsed hour:Q", y="Ethanol (g/L):Q", tooltip=["Elapsed hour", "Ethanol (g/L)"],
            )
        st.altair_chart(line, alt=f"{trend_label} through the replay clock")

    if forecasts:
        st.subheader("Discharge forecast history · Simulation only" if mode == SIMULATED_SPECTRA
                     else "Discharge forecast history")
        history = pd.DataFrame(forecasts)
        history["Issue hour"] = history["Issue minute"] / HOUR
        issue_axis = alt.X("Issue hour:Q", scale=alt.Scale(domain=[0, discharge / HOUR]))
        chart = alt.Chart(history).mark_line(point=True).encode(
            x=issue_axis, y=alt.Y("Predicted ethanol (g/L):Q", scale=alt.Scale(zero=False)),
            tooltip=["Issue hour", alt.Tooltip("Predicted ethanol (g/L):Q", format=".2f")],
        )
        if mode != SPECTRAL:
            checkpoint = pd.DataFrame({"Issue hour": [30], "Checkpoint": ["Six hours to discharge"]})
            chart += alt.Chart(checkpoint).mark_rule(strokeDash=[4, 3], color="gray").encode(
                x=issue_axis, tooltip=["Checkpoint:N"],
            )
            st.caption("The dashed line marks the hour-30 checkpoint.")
        st.altair_chart(chart, alt="Pre-discharge ethanol forecasts by issue time")
    elif mode != SPECTRAL:
        st.subheader("Discharge forecast history")
        st.caption("Forecasts will appear here as they become available.")

    st.subheader("Recent readings")
    if readings:
        recent = []
        for row in reversed(readings[-5:]):
            record = {"Elapsed time": clock_label(row.minute), "Ethanol (g/L)": round(row.ethanol, 2)}
            if spectral:
                record["NIR row label" if mode == SPECTRAL else "Spectrum minute key"] = row.source_row
            else:
                record["Temperature (°C)"] = row.temperature
                record["pH"] = row.ph
            recent.append(record)
        st.dataframe(recent, hide_index=True, alt="Five latest released concentrations")
    if lab is not None and now >= discharge:
        st.metric("Final simulated ethanol reference", f"{lab:.1f} g/L")
        st.caption(f"Sampled and released at {clock_label(discharge)} in the replay.")


def show_accuracy(database, load_snapshot, replay, metrics, now, lab):
    mode = replay["mode"]
    with st.expander("Accuracy and how to improve it"):
        if mode == SPECTRAL:
            show_calibration_accuracy(database, load_snapshot)
        elif mode == SYNTHETIC:
            st.markdown("**Saved Model 2 held-out synthetic performance**")
            st.dataframe(metrics[["Lead (h)", "Method", "Samples", "MAE (g/L)", "RMSE (g/L)"]],
                         hide_index=True, alt="Saved synthetic held-out accuracy by lead")
            st.caption("These aggregates use 80 independent held-out synthetic batches per lead. "
                       "The operator showcases are separate examples.")
            st.write("Ridge was more accurate at 12 and 6 hours by MAE. The two-hour extrapolation baseline was "
                     "more accurate at the shortest lead. A lead-specific fit could test whether that late gap narrows.")
            show_example_error(replay, lab)
            st.write("Independent factory batches with timestamped ethanol estimates, scheduled discharge, and "
                     "discharge assays would test whether these errors transfer to the plant.")
        else:
            st.markdown("**Same-trajectory input comparison · one example batch**")
            st.write("The two paths use the same Ridge fit and issue times. One uses the simulator's ethanol "
                     "directly. The other uses the saved PLS estimates from the illustrative spectra.")
            if now >= 30 * HOUR:
                rows = []
                for path, label in (("direct", "Direct simulated ethanol"), ("primary", "PLS from illustrative spectra")):
                    forecast = next(row for row in replay["forecasts"][path] if row["Issue minute"] == 30 * HOUR)
                    predicted = forecast["Predicted ethanol (g/L)"]
                    row = {"Input path": label, "Hour-30 forecast (g/L)": predicted}
                    if lab is not None:
                        row["Signed example error (g/L)"] = predicted - lab
                    rows.append(row)
                st.dataframe(rows, hide_index=True, alt="Two input paths on one simulated trajectory")
            if lab is None:
                st.caption("Hour-30 forecast comparisons appear at the checkpoint. Errors against the simulated "
                           "reference are available at hour 36.")
            else:
                show_example_error(replay, lab)
                last = {path: forecasts[-1]["Predicted ethanol (g/L)"] for path, forecasts in replay["forecasts"].items()}
                st.write(f"At hour 35 the two forecasts were {abs(last['primary'] - last['direct']):.2f} g/L apart. "
                         f"Even with direct simulator readings, Ridge missed the endpoint by "
                         f"{abs(last['direct'] - lab):.2f} g/L in this example.")
            st.write("The configured demo target is an operator threshold. Forecast error uses the simulated endpoint. "
                     "Real paired process spectra and discharge assays are needed to test this path on factory batches.")


def show_example_error(replay, lab):
    if lab is not None:
        last = replay["forecasts"]["primary"][-1]
        error = last["Predicted ethanol (g/L)"] - lab
        st.caption(f"Hour-35 signed example error against the released simulated endpoint · {error:+.2f} g/L.")


def show_calibration_accuracy(database, load_snapshot):
    st.markdown("**Model 1 calibration · held-out evaluation separate from the timeline**")
    try:
        result = saved_ethanol_evaluation(RELEASE, database, load_snapshot)
    except (DatasetError, ValueError, KeyError) as error:
        st.error(f"{error} {RECOVERY}")
        return
    row = next(item for item in result["metrics"] if item["Split"] == "Held-out test")
    st.write(f"{row['Samples']} held-out samples · MAE {row['MAE']:.3f} g/L · RMSE {row['RMSE']:.3f} g/L")
    frame = result["predictions"].rename(columns={"Measured": "Measured ethanol (g/L)",
                                                 "Predicted": "Estimated ethanol (g/L)"})
    x, y = "Measured ethanol (g/L)", "Estimated ethanol (g/L)"
    frame["Signed error (g/L)"] = frame[y] - frame[x]
    st.dataframe(frame, hide_index=True, alt="Saved Model 1 ethanol estimates, measurements and signed errors")
    values = frame[[x, y]].to_numpy()
    domain = [float(values.min()), float(values.max())]
    scale = alt.Scale(domain=domain, zero=False)
    axes = {"x": alt.X(f"{x}:Q", scale=scale), "y": alt.Y(f"{y}:Q", scale=scale)}
    diagonal = alt.Chart(pd.DataFrame({x: domain, y: domain})).mark_line(strokeDash=[5, 4], color="gray")
    dots = alt.Chart(frame).mark_point(filled=True).encode(tooltip=["Source row label", x, y, "Signed error (g/L)"])
    st.altair_chart((diagonal + dots).encode(**axes), alt="Held-out Model 1 measured versus estimated ethanol")
    st.caption("Signed error is estimate minus measured ethanol. The replay follows source order, so estimates can "
               "fluctuate across rows. Factory evaluation needs independently sampled spectra and paired assays.")


def show_model_2_details(model, validation, test, metrics, sizes):
    with st.expander("Model 2 details and validation"):
        st.table(pd.DataFrame([
            {"Data": "Input X", "Per forecast window": "One row with 3 features",
             "Contents": "Latest ethanol (g/L), two-hour ethanol slope (g/L/h), hours remaining to discharge"},
            {"Data": "Output y", "Per forecast window": "One value",
             "Contents": "Final ethanol reference in g/L"},
        ]), hide_index=True, alt="Model 2 inputs and output per forecast window")
        st.dataframe(sizes, hide_index=True, alt="Input and output dimensions, batch counts and forecast windows by split")
        st.caption("All windows from a batch share that batch's endpoint reference.")
        st.write("The direct path uses simulated ethanol readings. The synthetic spectral batch uses spectra → "
                 "Model 1 ethanol PLS → timestamped ethanol estimates. Both use the saved Ridge fit.")
        st.markdown("**Ridge objective**")
        st.latex(r"\min_{b,\mathbf{w}}\sum_i(y_i-b-\mathbf{w}^\top\mathbf{z}_i)^2+\alpha\lVert\mathbf{w}\rVert_2^2")
        st.caption("Ridge minimises squared discharge prediction errors plus an alpha-weighted penalty on the three "
                   "coefficients. The intercept is fitted without a penalty.")
        st.markdown("**Prediction equation**")
        st.latex(r"\widehat{y}_{\mathrm{discharge}}=b+w_1 z_1+w_2 z_2+w_3 z_3,\qquad z_j=(x_j-\mu_j)/\sigma_j")
        st.caption("Each feature is centred and scaled using training statistics before multiplying by its fitted "
                   "coefficient. The resulting sum plus the intercept predicts ethanol in g/L.")
        st.markdown("**Parameters solved**")
        st.write(f"Fitted intercept **{model['intercept']:.6f} g/L**.")
        st.dataframe(pd.DataFrame({"Feature": FEATURES, "Training mean": model["mean"],
                                   "Training scale": model["scale"], "Standardized Ridge coefficient": model["weights"]}),
                     hide_index=True, alt="Fitted Model 2 scaler and coefficients")
        st.caption("The fit estimates the intercept and coefficients. Validation selects alpha by the lowest MAE.")
        st.write(f"Selected alpha **{model['alpha']:g}**.")
        st.dataframe(validation, hide_index=True, alt="Candidate Ridge alphas and validation MAE")
        st.markdown("**Training and test split**")
        st.write(f"The statistical generator in model_2.py uses seed {SEED}, varies the ethanol histories by batch, "
                 "and adds separate assay noise to the simulated hour-36 reference. The three operator showcases "
                 "are excluded. Each batch stays in one split and each forecast uses only ethanol readings "
                 "released by its issue time.")
        st.dataframe(sizes[["Split", "Batches", "Windows"]], hide_index=True, alt="Actual batch and window counts")
        st.subheader("Synthetic held-out results")
        st.caption("The trend baseline adds the latest ethanol to its two-hour slope multiplied by time remaining. "
                   "Both methods use the same batches and issue times.")
        st.dataframe(metrics, hide_index=True, alt="Synthetic held-out forecast errors and alert counts",
                     column_config={column: st.column_config.NumberColumn(format="%.3f")
                                    for column in ("MAE (g/L)", "MSE ((g/L)²)", "RMSE (g/L)", "Bias (g/L)")})
        st.caption("MAE is the mean absolute error in g/L. MSE is the mean squared error in (g/L)². "
                   "RMSE is the square root of MSE in g/L. Bias is the mean signed prediction error. "
                   "Missed shortfalls are counted among actual results below 130 g/L. False warnings are counted "
                   "among actual results at or above 130 g/L.")
        lead = st.selectbox("Evaluation lead time (hours)", (12, 6, 2), index=1, key="model_2_eval_lead")
        points = test.loc[test[FEATURES[-1]] == lead].melt(
            id_vars=["Batch", "Reference (g/L)"], value_vars=["Ridge", "Trend baseline"],
            var_name="Method", value_name="Predicted (g/L)",
        )
        values = points[["Reference (g/L)", "Predicted (g/L)"]].to_numpy()
        domain = [float(values.min()), float(values.max())]
        diagonal = pd.DataFrame({"Reference (g/L)": domain, "Predicted (g/L)": domain})
        scale = alt.Scale(domain=domain, zero=False)
        x, y = alt.X("Reference (g/L):Q", scale=scale), alt.Y("Predicted (g/L):Q", scale=scale)
        line = alt.Chart(diagonal).mark_line(strokeDash=[5, 4], color="gray").encode(x=x, y=y)
        dots = alt.Chart(points).mark_point(filled=True, opacity=.7).encode(
            x=x, y=y, color="Method:N", tooltip=["Batch", "Method", "Reference (g/L)", "Predicted (g/L)"],
        )
        st.altair_chart(line + dots, alt="Synthetic held-out discharge predictions versus reference, with equality line")
        st.caption("The spectral demo has simulated timing and no independent discharge reference for accuracy evaluation.")
