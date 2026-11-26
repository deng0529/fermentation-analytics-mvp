import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from batch_monitor import show_batch as show_batch_monitor
from data_provenance import show_data_sources, show_model_1_source
from example_data import SOURCES
from explorer_plots import channel_scatter, spectral_overlay
from results_store import RECOVERY, load_calibration
from nir_calibration import make_nir_split
from nir_source import NIR_URL
from spectral_store import NIR, load_versioned_dataset
from turso_database import DatasetError, connect

SPLIT_ROLES = {"Training": "Fit the model", "Validation": "Choose model settings",
               "Test": "Evaluate the final model"}
TARGETS = ("Ethanol", "Glucose")


def table(rows, label):
    st.dataframe(rows, hide_index=True, width="stretch", alt=label)


def style_altair(chart, *, legend_columns):
    return (
        chart.configure_axis(labelFontSize=14, titleFontSize=15)
        .configure_legend(orient="bottom", columns=legend_columns, title=None, labelFontSize=14)
    )


def show_batch():
    show_batch_monitor(results_database, load_nir_snapshot)


def show_model_input_output(input_detail, output_detail, inputs, references, target_label):
    st.subheader("Model input and output")
    for column, label, detail in zip(st.columns(2), ("Input", "Output"), (input_detail, output_detail), strict=True):
        with column.container(border=True, height="stretch", key=f"model-card-{label.lower()}"):
            st.markdown(f"**{label}**")
            st.write(detail)

    st.markdown("**Dataset dimensions**")
    st.markdown(
        f"{inputs.shape[0]:,} input rows × {inputs.shape[1]:,} features  \n"
        f"{references.shape[0]:,} reference rows × {references.shape[1]:,} {target_label}"
    )


def show_nir_split(split):
    st.markdown("**Shared sample split**")
    counts = [
        f"**{partition} · {len(rows)}** — {SPLIT_ROLES[partition]}"
        for partition, rows in split["display_indexes"].items()
    ]
    st.markdown("  \n".join(counts))
    st.caption(f"Seed {split['seed']}. Each assignment keeps the spectrum with its lab reference. "
               "Ethanol, glucose, PLS, and SVR share the same assignments.")


def show_nir_preprocessing(compound):
    _, frames, _ = load_nir_snapshot()
    spectra, references = frames["calibration"]
    features = spectra.drop(columns="_row")
    channels = tuple(features.columns)
    reference = references[[compound]]
    paired = features.index.equals(references.index)
    with st.container(border=True, key="panel-inputs"):
        show_model_input_output(
            f"{len(channels):,} first-derivative absorbance values per sample",
            f"One {compound.lower()} concentration in g/L per sample",
            features, reference, "selected target",
        )
        st.caption(f"Exact reference column · `{compound}`")
        st.caption("The source reference table contains both `Ethanol` and `Glucose`.")
        channel = channels[0]
        wavelength = int(float(channel[1:]))
        st.write(f"`X{wavelength}` (loaded as `{channel}`) identifies the wavelength channel at {wavelength} nm. "
                 "The number in that column is the first derivative of absorbance at that wavelength for this sample.")

    with st.container(border=True, key="panel-preprocessing"):
        st.subheader("Source preprocessing and data checks")
        st.write("The published NIR spectra are already supplied as first derivatives. "
                 "This page applies no additional transformation.")
        st.caption(f"[chemometrics NIR documentation]({SOURCES['chemometrics::NIR']['url']})")
        for label, frame in (("Spectral inputs", features), ("Both lab reference columns", references)):
            missing = frame.isna().to_numpy().sum()
            infinite = np.isinf(frame.to_numpy(dtype=float)).sum()
            st.write(f"**{label}** · {missing:,} missing values · {infinite:,} infinite values")
        status = "match by source row position" if paired else "do not match"
        st.write(f"**Row check** · {len(features)} input rows and {len(references)} reference rows {status}.")
        st.caption("The source reference table has no independent sample IDs. Pairing uses the published row order.")

    if not paired:
        raise ValueError("NIR inputs and references must share the same row index.")
    split = make_nir_split(features.index)
    with st.container(border=True, key="panel-split"):
        st.subheader("Training, validation and testing")
        show_nir_split(split)


def show_preprocessing():
    st.title("Preprocessing & Feature Selection")
    with st.container(border=True, key="panel-dataset"):
        st.subheader("Calibration dataset")
        left, right = st.columns(2)
        left.selectbox("Dataset", [NIR], key="prep_source")
        compound = right.selectbox("Target", TARGETS, key="prep_nir_target")
        show_model_1_source()

    try:
        show_nir_preprocessing(compound)
    except (DatasetError, ValueError) as error:
        st.error(f"Could not prepare the source data. {error}")


@st.cache_data(show_spinner=False, max_entries=4)
def load_model_1a(version_id, target, _spectra, _references):
    return load_calibration(results_database(), target, _spectra.drop(columns="_row"))


def show_calibration():
    st.title("Model Training & Validation")
    options = {f"{NIR} — {target}": target for target in TARGETS}
    selection = st.selectbox("Experiment", list(options), index=None, placeholder="Select the data source",
                             key="model_1a_experiment")
    show_model_1_source(training=True)
    if selection is None:
        return
    target = options[selection]
    try:
        with st.spinner("Loading NIR from Turso…"):
            version_id, frames, _ = load_nir_snapshot()
        spectra, references = frames["calibration"]
        features, reference = spectra.drop(columns="_row"), references[[target]]
        with st.spinner(f"Loading the saved {target.lower()} experiment…"):
            fitted = load_model_1a(version_id, target, spectra, references)
        with st.container(border=True, key="panel-training-inputs"):
            show_model_input_output(
                f"{features.shape[1]} first-derivative absorbance values per sample",
                f"One {target.lower()} concentration in g/L per sample", features, reference, "selected target",
            )
            st.caption(f"Lab reference column · `{target}`. All {features.shape[1]} channels are used in source order.")
            indexes = fitted["config"]["indexes"]
            show_nir_split({"seed": fitted["config"]["seed"], "display_indexes": {
                "Training": indexes["Training"], "Validation": indexes["Validation"], "Test": indexes["Held-out test"],
            }})
    except (DatasetError, ValueError, KeyError) as error:
        st.error(f"{error} {RECOVERY}")
        return

    with st.container(border=True, key="panel-training-model"):
        settings = fitted["settings"]
        model_name = f"{settings['n_components']}-component PLS" if target == "Ethanol" else "Tuned RBF SVR"
        st.subheader(f"Model 1A · {target} · {model_name}")
        show_training_objective(target)
        show_fitted_equation(target, fitted)
        show_fitted_parameters(target, fitted)
    with st.container(border=True, key="panel-training-evaluation"):
        st.subheader("Evaluation")
        metrics = [{"Split": row["Split"], "Samples": row["Samples"], "MAE (g/L)": row["MAE"],
                    "RMSE (g/L)": row["RMSE"], "Bias (g/L)": row["Bias"]} for row in fitted["metrics"]]
        st.dataframe(metrics, hide_index=True, width="stretch", alt=f"{target} validation and held-out test metrics",
                     column_config={name: st.column_config.NumberColumn(format="%.6f")
                                    for name in ("MAE (g/L)", "RMSE (g/L)", "Bias (g/L)")})
        st.caption("Validation was used to choose settings. The held-out rows were used to check prediction performance.")
        st.subheader("Predicted versus measured")
        show_held_out_plot(fitted["predictions"], target)
        with st.expander("Saved training candidates and comparison"):
            st.caption("PLS candidates were ranked by validation MAE. SVR candidates were ranked by validation RMSE.")
            st.dataframe([{"Method": row["method"], "Settings": str(row["settings"]),
                           "Validation MAE (g/L)": row.get("validation", {}).get("MAE"),
                           "Validation RMSE (g/L)": row.get("validation", {}).get("RMSE"),
                           "Held-out MAE (g/L)": row.get("test", {}).get("MAE"),
                           "Held-out RMSE (g/L)": row.get("test", {}).get("RMSE"),
                           "Method winner": row["winner"]} for row in fitted["candidates"]],
                         hide_index=True, alt="Saved Model 1 training candidate and comparison results")


def parameter_table(frame, label, filename, caption):
    table(frame, label)
    st.caption(caption)
    st.download_button(f"Download {label} CSV", frame.to_csv(index=False, float_format="%.17g"),
                       file_name=filename, mime="text/csv", on_click="ignore")


def show_training_objective(target):
    st.subheader("Training objective and constraints")
    if target == "Ethanol":
        st.markdown("**A. Build the spectral components**")
        st.latex(r"\max_w \operatorname{Cov}(X_r w, y_r)^2 \quad \text{subject to } \lVert w\rVert_2=1")
        st.write("At each step, Xᵣ and yᵣ are the remaining training spectra and ethanol references, "
                 "and the unit-length weights w combine wavelengths into a score on a fixed scale. "
                 "PLS chooses scores with high covariance with the remaining ethanol values and accounts for "
                 "that component before extracting the next one.")

        st.markdown("**B. Fit the regression on the component scores**")
        st.latex(r"\min_{b_T,c}\ \lVert y - b_T\mathbf{1} - Tc \rVert_2^2")
        st.write("T contains 10 scores per training sample. Least squares fits the intercept bₜ and one weight "
                 "in c per score to reduce squared errors against the ethanol references y.")
    else:
        st.latex(r"\min_{w,b,\xi,\xi^*}\ \frac{1}{2}\lVert w\rVert^2+C\sum_i(\xi_i+\xi_i^*)")
        st.write("The size of the weight vector w penalizes model complexity. C sets the penalty on the slacks "
                 "ξᵢ and ξᵢ*, which measure errors beyond the epsilon band.")
        st.latex(r"""
            \begin{aligned}
            y_i-f(z_i) &\leq \epsilon+\xi_i \\
            f(z_i)-y_i &\leq \epsilon+\xi_i^* \\
            \xi_i,\xi_i^* &\geq 0 \\
            f(z) &= w^\top\phi(z)+b
            \end{aligned}
        """)
        st.write("Errors between the reference yᵢ and prediction f(zᵢ) incur no slack penalty inside the epsilon band. "
                 "Beyond it, ξᵢ covers underprediction and ξᵢ* covers overprediction.")
        st.write("The feature map φ represents the scaled spectrum z in the RBF kernel’s feature space. "
                 "The prediction uses weights w and intercept b in that space.")


def show_fitted_equation(target, fitted):
    st.subheader("Fitted prediction equation")
    if target == "Ethanol":
        st.latex(r"\widehat{\mathrm{ethanol}} = b + k_1 x_1 + \cdots + k_{235} x_{235}")
        st.write("Each x is a published first-derivative absorbance value and each k is its fitted coefficient. "
                 "The 10 learned components combine those 235 inputs, and the final equation uses the original "
                 "inputs and intercept b to predict ethanol in g/L.")
    else:
        st.latex(r"\widehat{\mathrm{glucose}} = b+\sum_{i\in\mathcal{S}}\beta_i\exp\!\left(-\gamma\lVert z-s_i\rVert^2\right)")
        st.write("The fitted intercept is b, z is the scaled input spectrum, and each support spectrum sᵢ in the set S "
                 "has a signed weight βᵢ. Each term uses the similarity between z and sᵢ to predict glucose in g/L.")
        st.latex(r"z_j = (x_j-\mu_j)/\sigma_j")
        st.write("For wavelength j, subtract the training mean μⱼ from the original reading xⱼ and divide by the "
                 "training scale σⱼ. Apply the same conversion to every new spectrum.")
    st.caption(f"Equation check · maximum difference from estimator predictions over 25 held-out samples "
               f"{fitted['max_error']:.3g} g/L.")


def show_fitted_parameters(target, fitted):
    st.subheader("Fitted parameters and model settings")
    settings = fitted["settings"]
    if target == "Ethanol":
        st.markdown("**Learned during fitting**")
        with st.expander("Learned component and score weights"):
            table(fitted["component_weights"], "Learned wavelength weights for each PLS component")
            st.caption("Each column gives the wavelength weights used to build one component from the remaining spectra.")
            table(fitted["score_weights"], "Learned regression weights on PLS scores")
            st.caption("Each row gives the change in predicted ethanol, in g/L, per unit increase in that score.")
        st.markdown("**Final prediction parameters**")
        st.write(f"Effective intercept b = {fitted['intercept']:.17g} g/L")
        with st.expander("Fitted wavelength coefficients"):
            parameter_table(
                fitted["coefficients"], "wavelength coefficients", "model_1a_ethanol_coefficients.csv",
                "The effective intercept and these coefficients express the component-based fit in the original "
                "wavelength coordinates. The rows follow the source order.",
            )
        st.write(f"**Model settings** · {settings['n_components']} components · PLS scale = {settings['scale']}")
        st.write("PLS centers and scales the input channels and ethanol references using the training rows. "
                 "Ten components gave the lowest validation MAE among the PLS candidates.")
    else:
        st.markdown("**Final prediction parameters**")
        st.write(f"Intercept b = {fitted['intercept']:.17g} g/L  \nSupport vectors · {len(fitted['support'])}")
        st.write("Training determines which spectra become support vectors and assigns their signed weights. "
                 "The slack variables describe how training handles errors outside the band.")
        with st.expander("Support spectra and signed weights"):
            parameter_table(
                fitted["support"], "support spectra and signed weights", "model_1a_glucose_support_vectors.csv",
                "Each row contains a support spectrum in scaled coordinates and its signed prediction weight.",
            )
        with st.expander("Fitted feature scaler"):
            parameter_table(
                fitted["scaler"], "feature scaler", "model_1a_glucose_feature_scaler.csv",
                "Each row gives the training mean and scale for one wavelength in source order.",
            )
        st.write(f"**Model settings** · {settings['kernel'].upper()} kernel · C = {settings['C']:g} · "
                 f"γ ≈ {settings['gamma']:.12g} · ε = {settings['epsilon']:g} g/L")
        st.markdown(
            "- **RBF** measures similarity between spectra in scaled coordinates.\n"
            "- **C** sets the penalty for errors outside the epsilon band.\n"
            "- **Gamma** controls how quickly similarity falls with distance.\n"
            "- **Epsilon** sets the tolerated error on either side of the prediction."
        )


def show_held_out_plot(predictions, target):
    values = predictions[["Measured", "Predicted"]].to_numpy()
    lower, upper = float(values.min()), float(values.max())
    margin = (upper - lower) * 0.05
    domain = [lower - margin, upper + margin]
    scale = alt.Scale(domain=domain, nice=False, zero=False)
    x = alt.X("Measured:Q", title=f"Measured {target.lower()} (g/L)", scale=scale)
    y = alt.Y("Predicted:Q", title=f"Predicted {target.lower()} (g/L)", scale=scale)
    ideal = pd.DataFrame({"Measured": domain, "Predicted": domain})
    line = alt.Chart(ideal).mark_line(strokeDash=[6, 4], color="#64748b").encode(x=x, y=y)
    dots = alt.Chart(predictions).mark_point(filled=True, size=68, color="#08796d").encode(
        x=x, y=y, tooltip=[alt.Tooltip("Source row position:Q", format="d"), "Source row label:N",
                          alt.Tooltip("Measured:Q", format=".3f"), alt.Tooltip("Predicted:Q", format=".3f")],
    )
    chart = (line + dots).properties(height=360).configure_axis(labelFontSize=14, titleFontSize=15)
    st.altair_chart(chart, width="stretch", alt=f"{target} predicted versus measured for 25 held-out samples")
    st.caption("Each dot is one test sample. Points above the line are overpredictions. "
               "Points below the line are underpredictions.")


def results_database():
    try:
        secrets = st.secrets.to_dict()
    except FileNotFoundError:
        secrets = {}
    return connect(secrets)


@st.cache_data(ttl=300, show_spinner=False)
def load_nir_snapshot():
    return load_versioned_dataset(NIR, database=results_database())


def show_data_explorer():
    st.title("Data Explorer")
    datasets = [
        (f"[chemometrics::NIR]({NIR_URL})", "Model 1A calibration",
         "Mixed — numerical spectra and concentrations, with text row labels"),
        ("Synthetic batches", "Model 2 discharge forecasting",
         "Mixed — numerical process readings and endpoint references, with text batch labels"),
    ]
    with st.container(border=True, key="panel-inventory"):
        st.subheader("Dataset inventory")
        st.caption(f"{len(datasets)} datasets")
        st.markdown(
            "| Data source | Purpose | Data type |\n"
            "| --- | --- | --- |\n"
            + "\n".join(f"| {name} | {purpose} | {kind} |" for name, purpose, kind in datasets)
        )
        show_data_sources()

    with st.container(border=True, key="panel-inspection"):
        st.subheader("Inspect a spectral dataset")
        st.selectbox("Inspect dataset", [NIR])
        with st.spinner("Loading NIR from Turso…"):
            try:
                _, frames, _ = load_nir_snapshot()
            except DatasetError as error:
                st.error(str(error))
                return
        show_nir_tables(*frames["calibration"])


def show_paired_figures(spectra, coordinates, measured, labels, coordinate_title, signal_title, target, key):
    st.markdown("##### Spectral overlay")
    st.plotly_chart(
        spectral_overlay(spectra, coordinates, measured, labels, coordinate_title, signal_title, target),
        key=f"{key}_overlay", width="stretch", alt=f"Spectra coloured by measured {target.lower()}",
    )
    st.caption(
        "Each line shows one sample across all wavelengths. The height shows how quickly absorbance "
        "changes at that wavelength. At any one wavelength, there is one reading per sample. "
        f"The colour of each line shows the sample’s measured {target.lower()} in g/L."
    )
    st.markdown("##### Selected channel vs reference concentration")
    channels = {str(channel): channel for channel in spectra.columns}
    label = st.selectbox("Spectral channel", channels, key=f"{key}_channel")
    channel = channels[label]
    st.plotly_chart(
        channel_scatter(spectra[channel], measured, labels, f"{signal_title} · {channel}", target),
        key=f"{key}_scatter", width="stretch", alt=f"Channel {channel} versus measured {target.lower()}",
    )
    st.caption(
        f"Each dot is one sample. Across the bottom is the sample’s absorbance slope at {float(channel[1:]):g} nm. "
        f"Up the side is its lab-measured {target.lower()} in g/L."
    )


def show_nir_tables(spectra, references):
    channels = spectra.columns.drop("_row")
    first, second, last = channels[0], channels[1], channels[-1]
    reference_names = ", ".join(f"`{name}`" for name in references.columns)
    st.markdown(
        "#### Dataset summary\n\n"
        "| Component | Rows | Measurement columns | Purpose |\n"
        "| --- | ---: | ---: | --- |\n"
        f"| `xNIR` | {len(spectra)} | {len(channels)} | Spectral inputs |\n"
        f"| `yGlcEtOH` | {len(references)} | {len(references.columns)} | Reference concentrations |"
    )
    st.caption(
        f"Missing values · xNIR: {spectra.isna().sum().sum()} · "
        f"yGlcEtOH: {references.isna().sum().sum()}"
    )
    st.markdown(
        f"**xNIR.** Each row is the spectrum of one alcoholic fermentation mash sample. "
        "Each spectral cell is the published first derivative of NIR absorbance at the column’s wavelength. "
        f"The numeric part of the `X` header is the wavelength in nm. "
        f"`{first}` is the first spectral column (1115 nm), `{second}` is 1120 nm, "
        f"and `{last}` is the last spectral column (2285 nm). "
        "The final JSON field, `_row`, contains the source row label and is excluded from spectral inputs. "
        "[NIR dataset documentation](https://search.r-project.org/CRAN/refmans/chemometrics/html/NIR.html)"
    )
    st.markdown(
        f"**yGlcEtOH.** Each row contains the reference concentrations for one mash sample. "
        f"The columns, in source order, are {reference_names}. "
        "`Glucose` is the glucose reference and `Ethanol` is the ethanol reference, both in g/L."
    )
    st.markdown(
        "**X–Y pairing.** Match the same row position in both components. The package’s example "
        "combines input and reference rows using the same positions. Only xNIR supplies `_row`, "
        "so there is no shared identifier to join on. The app adds the same 1-based **Display index** "
        "to both tables. It is excluded from the source column counts and model inputs. "
        "[Package pairing example](https://filzmoserp.r-universe.dev/chemometrics/doc/manual.html#stepwise)"
    )
    position = spectra.index[0]
    spectral_row, reference_row = spectra.loc[position], references.loc[position]
    st.markdown(
        f"**Paired example · Display index {position}.** "
        f"xNIR row label `{spectral_row['_row']}` has `{first}` = `{spectral_row[first]}`. "
        f"The matching yGlcEtOH row contains Glucose **{reference_row['Glucose']} g/L** "
        f"and Ethanol **{reference_row['Ethanol']} g/L**."
    )
    spectral_tab, reference_tab = st.tabs(["xNIR · Spectral inputs", "yGlcEtOH · Reference concentrations"])
    index = st.column_config.NumberColumn(
        "Display index", help="1-based row position in the published JSON", pinned=True, format="%d",
    )
    with spectral_tab:
        st.dataframe(
            spectra, height=480, hide_index=False, width="stretch",
            column_config={
                "_index": index,
                **{channel: st.column_config.NumberColumn(format="plain") for channel in channels},
            },
            alt="Complete published xNIR spectral matrix and original row labels",
        )
    with reference_tab:
        st.dataframe(
            references, height=480, hide_index=False, width="stretch",
            column_config={
                "_index": index,
                **{compound: st.column_config.NumberColumn(format="plain") for compound in references.columns},
            },
            alt="Complete published yGlcEtOH glucose and ethanol reference concentrations",
        )
    target = st.selectbox("Reference concentration", ["Glucose", "Ethanol"], key="nir_plot_target")
    show_paired_figures(
        spectra.loc[:, channels], [float(name[1:]) for name in channels], references[target],
        [f"Source row: {label}<br>Display index: {position}" for position, label in spectra["_row"].items()],
        "Wavelength (nm)", "First derivative of NIR absorbance", target, "nir",
    )


def show_home():
    cards = (
        ("Data Explorer", "Explore NIR spectra and paired lab measurements.", "NIR spectra · Lab references"),
        ("Preprocessing & Feature Selection", "See how the data are prepared and which inputs each model uses.",
         "First-derivative NIR · Spectral features"),
        ("Model Training & Validation", "Review the fitted ethanol and glucose calibrations and their test results.",
         "Model 1 · Ethanol PLS · Glucose RBF SVR"),
        ("Batch Monitor", "Replay a batch and follow its ethanol trend and discharge forecast where available.",
         "Model 2 · Ridge regression"),
    )
    with st.container(horizontal_alignment="center"):
        with st.container(width=900, key="home-dashboard", gap="large"):
            st.html("""
            <style>
            [data-testid="stMain"]:has(.st-key-home-dashboard) { background: #f1f5f9; }
            .st-key-home-dashboard { padding-block: clamp(2rem, 6vw, 5.25rem) 2rem; }
            .st-key-home-intro h1 {
                color: #14263b;
                font-size: clamp(2.125rem, 5.2vw, 3.25rem);
                line-height: 1.12;
                font-weight: 700;
                letter-spacing: -0.035em;
                text-align: center;
            }
            .st-key-home-intro p {
                max-width: 39rem;
                margin-inline: auto;
                color: #42546a;
                text-align: center;
                line-height: 1.6;
            }
            .st-key-home-dashboard [class*="st-key-home-card-"] {
                position: relative;
                box-sizing: border-box;
                height: 100%;
                min-height: 11.5rem;
                padding: clamp(1.125rem, 2.5vw, 1.75rem);
                background: #fff;
                border: 1px solid #d9e3eb;
                border-radius: 12px;
                transition: border-color 150ms ease, box-shadow 150ms ease;
            }
            .st-key-home-dashboard [class*="st-key-home-card-"]:hover {
                border-color: #7caaa8;
                box-shadow: 0 4px 16px #14263b0d;
            }
            .st-key-home-dashboard [class*="st-key-home-card-"]:has(a:focus-visible) {
                outline: 3px solid #00716d;
                outline-offset: 3px;
            }
            .st-key-home-dashboard [data-testid="stPageLink"] a:focus-visible { outline: none; }
            .st-key-home-dashboard [data-testid="stPageLink"] a {
                position: static;
                min-height: 0;
                padding: 0;
                border: 0;
                background: transparent;
                justify-content: flex-start;
                text-align: left;
                white-space: normal;
            }
            /* Extend the existing Streamlit link over its card without adding a tab stop. */
            .st-key-home-dashboard [class*="st-key-home-card-"] [data-testid="stElementContainer"],
            .st-key-home-dashboard [data-testid="stPageLink"] { position: static; }
            .st-key-home-dashboard [data-testid="stPageLink"] a::after {
                content: "";
                position: absolute;
                inset: 0;
                z-index: 1;
            }
            .st-key-home-dashboard [data-testid="stPageLink"] a p {
                color: #14263b;
                font-size: 1.125rem;
                font-weight: 600;
                line-height: 1.3;
                white-space: normal;
                overflow-wrap: anywhere;
            }
            .st-key-home-dashboard [class*="st-key-home-card-"]:is(:hover, :focus-within) a p { color: #006864; }
            .st-key-home-dashboard [class*="st-key-home-card-"] p { line-height: 1.5; }
            .st-key-home-dashboard [class*="st-key-home-card-"] [data-testid="stCaptionContainer"] p {
                color: #006864;
                font-weight: 600;
            }
            .st-key-home-dashboard [data-testid="stCaptionContainer"] { opacity: 1; }
            @media (prefers-reduced-motion: reduce) {
                .st-key-home-dashboard [class*="st-key-home-card-"] { transition: none; }
            }
            </style>
            """)
            with st.container(key="home-intro", gap="small"):
                st.title("Fermentation Analytics", anchor=False)
                st.write("Explore spectral data, estimate ethanol and glucose, and forecast ethanol at batch discharge.")
            with st.grid(2, min_column_width=300, gap="medium"):
                for title, description, keywords in cards:
                    module = module_pages[title]
                    with st.container(border=True, key=f"home-card-{module.url_path}", gap="small"):
                        st.page_link(module, label=title, width="stretch")
                        st.write(description)
                        st.caption(keywords)


st.set_page_config(page_title="Fermentation Analytics MVP", layout="wide")
module_pages = {
    "Data Explorer": st.Page(show_data_explorer, title="Data Explorer", url_path="data-explorer"),
    "Preprocessing & Feature Selection": st.Page(
        show_preprocessing, title="Preprocessing & Feature Selection", url_path="preprocessing"
    ),
    "Model Training & Validation": st.Page(show_calibration, title="Model Training & Validation", url_path="training"),
    "Batch Monitor": st.Page(show_batch, title="Batch Monitor", url_path="batch-monitor"),
}
home_page = st.Page(show_home, title="Home", default=True)
page = st.navigation([home_page, *module_pages.values()], position="hidden")

# Native bordered containers do not expose a surface color.
st.html("""
<style>
[class*="st-key-panel-"] { background-color: #ffffff; }
[data-testid="stCaptionContainer"] p { font-size: 15px; }
[data-testid="stWidgetLabel"] p { font-size: 16px; }
[data-testid="stMarkdownContainer"] :is(th, td) { font-size: 15px; }
.st-key-model-card-input p,
.st-key-model-card-output p { font-size: 15px; }
</style>
""")
with st.container(horizontal_alignment="center"):
    with st.container(width=1080, gap="medium"):
        if page is not home_page:
            st.page_link(home_page, label="← Back to Home")
        page.run()
