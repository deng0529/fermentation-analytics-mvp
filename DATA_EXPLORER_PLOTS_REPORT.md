# Data Explorer plots report

Verified locally on 25 November 2026. The Streamlit app is running at [http://127.0.0.1:8502/](http://127.0.0.1:8502/), with Data Explorer as the landing page. The health endpoint returned `ok`.

## Figures and coverage

| View | Figures and axes | Plotted data |
| --- | --- | --- |
| chemometrics::NIR | Spectral overlay uses wavelength (nm) and first derivative of NIR absorbance. The scatter uses the selected channel signal and measured glucose or ethanol (g/L). The overlay colour bar follows the same target in g/L. | 166 spectra across 235 wavelengths, and 166 paired dots for either target. Hover shows the source row label and display index. |
| chemotools Training | Spectral overlay uses wavenumber (cm⁻¹) and absorbance (a.u.). The scatter uses the selected channel absorbance and measured glucose (g/L). The overlay colour bar shows measured glucose in g/L. | 21 spectra across 1,047 wavenumbers, and 21 paired dots. Hover shows the loader’s source index. |
| chemotools Test | The upper heatmap shows estimated elapsed hours against wavenumber (cm⁻¹), coloured by packaged absorbance (a.u.). The lower panel shows individual measured glucose dots in g/L at recorded HPLC times. The panels share the elapsed-time axis. | 1,629 spectra across all 1,047 channels, and 34 HPLC dots. |
| Approximately matched test spectra | Expandable spectral overlay and selected-channel scatter with the same units as Training. Hover includes the spectrum and lab indexes, recorded lab time, estimated spectrum time, and signed time difference. | 34 pairs covering 34 distinct spectra. |

The published tables remain above the figures. Training and Test figures are shown within their respective tabs. [NIR source](https://filzmoserp.r-universe.dev/chemometrics/data/NIR/json) · [chemotools plotting guide](https://chemotools.org/learn/pls_regression.html#visualizing-the-training-data)

## Test timing and pairing

The code contained an explanation of nearest-time matching but no callable implementation. The new shared calculation converts zero-based spectrum position to elapsed hours using **1.25 minutes per spectrum**, with the first spectrum at zero. The last spectrum is therefore at about **33.91667 h**. Each in-range HPLC observation uses the nearest estimated spectrum, with equal distances resolved in acquisition order.

The heatmap and matched figures use the same estimated timeline. Lab dots and matched figures use the original glucose values, with no offset or interpolation. The signed time difference is estimated spectrum time minus recorded lab time. Per-spectrum timestamps remain unavailable, so the test matches are approximate.

## Verification

- Chrome confirmed source switching, both NIR targets, selected-channel changes for NIR, Training, and matched Test, the concentration colour bars, and the actual scatter counts of 166, 21, and 34. It also rendered the heatmap, counted 34 recorded lab dots, and confirmed the heatmap x-axis is linked to the lab x-axis.
- Figure-data checks confirmed the entire heatmap matches the source matrix in channel-by-spectrum order and that the test scatter uses exactly the 34 nearest-time pairs. All plotted test glucose values equal the source values.
- NIR display index 1 (`R1 zaM 1`) has a derivative of **0.0032** at 1115 nm and **0.0040** at 1120 nm. The plotted references were **9.781 g/L glucose** and **40.304 g/L ethanol**.
- Chemotools Training index 0 has **0.493506 a.u.** at 428.0 cm⁻¹ and **1.664707074 g/L** measured glucose.
- In the test timeline, spectrum index 0 has **1.878788 a.u.** at 428.0 cm⁻¹ and the first lab dot is **44.41567094 g/L** at 0 h. The lab reading at **0.666666667 h** matched spectrum index **32**, with **8.136364 a.u.** at 428.0 cm⁻¹ and **44.6426422 g/L** measured glucose.
- Python compilation and `pip check` passed. The local server stayed running and returned `ok`.

## Files changed

- [app.py](app.py) adds the figure sections and selectors to Data Explorer.
- [explorer_plots.py](explorer_plots.py) builds the figures and shares test timing and nearest-time matching.
- [requirements.txt](requirements.txt) declares NumPy and pins Plotly 7.2.0.
- This report records the implementation and checks.
