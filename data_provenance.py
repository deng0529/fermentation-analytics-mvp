"""Shared source citations and disclosure text for the Streamlit pages."""

import streamlit as st

from nir_source import NIR_URL
from replay_data import SIMULATED_SPECTRA, SPECTRAL
from spectral_store import CHEMOTOOLS_URI

NIR_CITATION = (
    "Liebmann, B., Friedl, A., & Varmuza, K. (2009). "
    "Determination of glucose and ethanol in bioethanol production by near infrared spectroscopy and chemometrics. "
    "*Analytica Chimica Acta, 642*(1–2), 171–178."
)
NIR_ARTICLE = "https://doi.org/10.1016/j.aca.2008.10.069"
NIR_REFERENCE = "https://search.r-project.org/CRAN/refmans/chemometrics/html/NIR.html"
NIR_PACKAGE = "https://cran.r-project.org/package=chemometrics"
CHEMOTOOLS_RELEASE = "https://pypi.org/project/chemotools/0.5.0/"
CHEMOTOOLS_ARTICLE = "https://doi.org/10.1002/bit.27586"

NIR_RIGHTS = (
    "CRAN lists the chemometrics package as GPL (≥ 3). Licence status for the underlying experimental records "
    "has not been confirmed separately. Public access alone does not establish permission to reuse, "
    "redistribute, or use the records commercially."
)
SIMULATION_LIMIT = (
    "Performance against simulated endpoint references does not establish accuracy on real industrial "
    "fermentation batches."
)


def show_nir_source():
    st.markdown(
        f"**NIR data (`chemometrics::NIR`)** · Experimental fermentation-mash records from the research of "
        f"Liebmann, Friedl and Varmuza at TU Wien (Vienna University of Technology). Peter Filzmoser maintains "
        f"the distributing R package. [Dataset documentation]({NIR_REFERENCE}) · [R-universe data]({NIR_URL})"
    )
    st.markdown(f"{NIR_CITATION} [Original publication]({NIR_ARTICLE})")
    st.markdown(f"{NIR_RIGHTS} [CRAN package and licence]({NIR_PACKAGE})")


def show_data_sources():
    with st.expander("Data Sources & References"):
        show_nir_source()
        st.write("The app pairs 166 source spectra with their glucose and ethanol references by row position. "
                 "Model 1 uses 116 training, 25 validation and 25 held-out pairs. Saved estimates and metrics "
                 "are outputs of this project’s fits.")
        st.markdown(
            f"**The Fermentation Dataset (`chemotools`)** · Historical ATR-FTIR package import maintained by "
            f"Pau Cabaneros Lopez. The package describes a synthetic calibration set and an experimental "
            f"fermentation test sequence. It is outside the active pages and published model runs. "
            f"[Dataset documentation]({CHEMOTOOLS_URI}) · [Associated 2021 research]({CHEMOTOOLS_ARTICLE})"
        )
        st.markdown(
            f"The Python package metadata lists MIT and the associated article is CC BY 4.0. "
            f"Licence status and reuse rights for the underlying data files have not been confirmed separately. "
            f"[Package licence metadata]({CHEMOTOOLS_RELEASE})"
        )
        st.markdown(
            "**Project development** · This project developed the app, snapshot and feature workflows, model "
            "integration, simulated replays and interactive displays. It uses established PLS, RBF SVR and Ridge "
            "estimators from [scikit-learn](https://scikit-learn.org/), with "
            "[Streamlit](https://streamlit.io/), [Plotly](https://plotly.com/python/) and "
            "[Altair](https://altair-viz.github.io/) for the interface and charts. External data, methods and "
            "libraries are credited to their respective sources."
        )


def show_model_1_source(*, training=False):
    with st.expander("NIR source, citation & licence"):
        show_nir_source()
        if training:
            st.write("Model 1 fits use 116 training rows. Candidate selection uses 25 validation rows. "
                     "The reported test metrics use 25 held-out rows from the same source dataset.")
        else:
            st.write("The published channels already contain first-derivative absorbance. "
                     "The app preserves their source order and pairs each row with its reference concentrations.")


def show_replay_source(mode):
    with st.expander("Replay data provenance"):
        if mode == SPECTRAL:
            show_nir_source()
            st.write("The replay clock assigns two minutes per public NIR row in source order. The plotted "
                     "concentrations are Model 1 predictions. The source provides no verified batch timeline "
                     "or scheduled discharge for this sequence.")
        elif mode == SIMULATED_SPECTRA:
            st.write("This demonstration generates illustrative spectra from templates averaged from Model 1 NIR "
                     "training rows. It adds seeded noise and assigns a simulated batch clock and endpoint. "
                     "It is outside both models’ fitting, tuning and aggregate held-out evaluation.")
            st.markdown(f"[NIR template source and citation]({NIR_REFERENCE}) · "
                        f"[Original NIR research]({NIR_ARTICLE})")
            st.write(NIR_RIGHTS)
            st.write(SIMULATION_LIMIT)
        else:
            st.write("These replay readings and endpoint references are project-generated showcase fixtures. "
                     "Model 2 is fitted and evaluated on a separate seeded synthetic generator with 240 training, "
                     "80 validation and 80 held-out batches. Discharge forecasts are model outputs.")
            st.write(SIMULATION_LIMIT)
