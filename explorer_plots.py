"""Figure builders for published spectra and measured lab references."""

import numpy as np
import plotly.graph_objects as go
from plotly.colors import sample_colorscale
from plotly.subplots import make_subplots
import pandas as pd

MINUTES_PER_SPECTRUM = 1.25
MIR_AXIS = "Wavenumber (cm⁻¹)"
MIR_SIGNAL = "Absorbance (a.u.)"
CONCENTRATION_SCALE = "Viridis"


def style_plotly(fig):
    fig.update_layout(font_size=14)
    fig.update_xaxes(automargin=True, tickfont_size=14, title_font_size=15)
    fig.update_yaxes(automargin=True, tickfont_size=14, title_font_size=15)
    return fig


def estimated_spectrum_hours(spectra):
    """Translate acquisition position to elapsed hours using the nominal cadence."""
    return np.arange(len(spectra)) * MINUTES_PER_SPECTRUM / 60


def match_test_spectra(spectra, references):
    """Keep one nearest spectrum per in-range lab observation, in lab source order."""
    hours = estimated_spectrum_hours(spectra)
    if not len(hours):
        return pd.DataFrame(columns=["spectrum_position", "lab_index", "lab_hour", "spectrum_hour",
                                     "delta_minutes", "glucose"])
    labs = references.loc[references["time"].between(hours[0], hours[-1]) & references["glucose"].notna()]
    distances = np.abs(labs["time"].to_numpy()[:, None] - hours)
    positions = distances.argmin(axis=1)
    return pd.DataFrame({
        "spectrum_position": positions,
        "lab_index": labs.index,
        "lab_hour": labs["time"].to_numpy(),
        "spectrum_hour": hours[positions],
        "delta_minutes": (hours[positions] - labs["time"].to_numpy()) * 60,
        "glucose": labs["glucose"].to_numpy(),
    })


def spectral_overlay(spectra, coordinates, measured, labels, coordinate_title, signal_title, target):
    measured = np.asarray(measured, dtype=float)
    lower, upper = measured.min(), measured.max()
    color_positions = (measured - lower) / (upper - lower) if upper > lower else np.full(len(measured), 0.5)
    colors = sample_colorscale(CONCENTRATION_SCALE, color_positions.tolist())
    target_title = f"{target} (g/L)"
    fig = go.Figure()
    for signal, concentration, label, color in zip(spectra.to_numpy(), measured, labels, colors, strict=True):
        fig.add_trace(go.Scattergl(
            x=coordinates, y=signal, mode="lines", line={"color": color, "width": 1.2},
            meta=[label, concentration], opacity=0.75, showlegend=False,
            hovertemplate=(f"%{{meta[0]}}<br>Measured {target.lower()}: %{{meta[1]}} g/L"
                           f"<br>{coordinate_title}: %{{x}}<br>{signal_title}: %{{y}}<extra></extra>"),
        ))
    # Plotly colors each trace with a single color. A zero-size marker provides its continuous scale.
    fig.add_trace(go.Scatter(
        x=[coordinates[0]] * 2, y=[spectra.iat[0, 0]] * 2, mode="markers", hoverinfo="skip", showlegend=False,
        marker={"size": 0, "color": [lower, upper], "cmin": lower, "cmax": max(upper, lower + 1e-12),
                "colorscale": CONCENTRATION_SCALE, "showscale": True, "colorbar": {"title": target_title}},
    ))
    fig.update_layout(
        xaxis_title=coordinate_title, yaxis_title=signal_title, height=420,
        margin={"t": 12, "r": 16, "b": 48, "l": 58},
    )
    return style_plotly(fig)


def channel_scatter(values, measured, labels, x_title, target):
    y_title = f"Measured {target.lower()} (g/L)"
    fig = go.Figure(go.Scatter(
        x=np.asarray(values), y=np.asarray(measured), text=labels, mode="markers",
        marker={"color": "#08796d", "size": 8, "opacity": 0.75},
        hovertemplate=f"%{{text}}<br>{x_title}: %{{x}}<br>{y_title}: %{{y}}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title=x_title, yaxis_title=y_title, height=345,
        margin={"t": 12, "r": 16, "b": 48, "l": 58},
    )
    return style_plotly(fig)


def test_timeline(spectra, references):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.08)
    fig.add_trace(go.Heatmap(
        x=estimated_spectrum_hours(spectra), y=spectra.columns.to_numpy(), z=spectra.to_numpy().T,
        colorscale="Viridis", colorbar={"title": MIR_SIGNAL, "len": 0.65, "y": 0.67},
        hovertemplate="Estimated spectrum time: %{x:.5f} h<br>Wavenumber: %{y} cm⁻¹"
                      "<br>Packaged absorbance: %{z}<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=references["time"].to_numpy(), y=references["glucose"].to_numpy(), mode="markers",
        marker={"color": "#08796d", "size": 8}, showlegend=False,
        hovertemplate="Recorded lab time: %{x} h<br>Measured glucose: %{y} g/L<extra></extra>",
    ), row=2, col=1)
    fig.update_xaxes(title_text="Elapsed time (h)", row=2, col=1)
    fig.update_yaxes(title_text=MIR_AXIS, row=1, col=1)
    fig.update_yaxes(title_text="Measured glucose (g/L)", row=2, col=1)
    fig.update_layout(height=630, margin={"t": 12, "r": 18, "b": 48, "l": 65})
    return style_plotly(fig)
