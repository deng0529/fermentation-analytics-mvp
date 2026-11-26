# Fermentation Analytics UI workflow redesign

Verified on 25 November 2026 on the local Windows Streamlit server. [Open the app](http://127.0.0.1:8502/). The health endpoint returned `ok`, and the server was left running.

The redesign follows the current app and the seven-step project scope supplied in chat. The named build-brief DOCX was unavailable in the project and the searched local folders, so it could not be independently reviewed.

## Final sidebar order

| Order | Page | Working today | Preview or later work |
| ---: | --- | --- | --- |
| 1 | **Data Explorer** · default | Browse the source inventory and complete published chemometrics::NIR and chemotools tables. The chemotools Training and Test tabs and timing explanation remain available. | Approximate spectrum-to-HPLC pairs are described. There was no implemented pair table to carry forward. |
| 2 | **Preprocessing & Feature Selection** | Choose the dataset and target, inspect actual source channel names and units, and select individual channels or an inclusive coordinate range. Review the selected count and confirm the ordered configuration. Confirmations are stored in the current session for each dataset and target. | Mean centering and standardisation are configuration previews. NIR already supplies first derivatives. |
| 3 | **Model Training & Validation** | View the confirmed configuration, edit PLS and SVR parameters, run a comparison preview, and inspect the results and run history. Options cover NIR ethanol, NIR glucose, and chemotools glucose. Each preview calculates MAE, RMSE, signed bias, and sample count from the same six illustrative reference pairs for both methods. | Fits and actual validation are planned. NIR will use shared training and held-out samples from the 166 source pairs. Chemotools will use the 21 training pairs and evaluate both methods against the same approximate nearest-time HPLC matches. |
| 4 | **Batch Monitor** | Replay synthetic batches in operator order. Review batch and source, current glucose and ethanol estimates, concentration trends and a revealable ethanol lab point, then the discharge forecast and target warning. Changing the batch resets the replay and clears the revealed result. | Concentration estimates and the discharge forecast currently come from synthetic fixtures. |

Training displays the exact ordered preprocessing steps and selected source channels for the current confirmed dataset and target. A preview result is eligible for the current comparison only when its confirmed configuration also matches. Earlier runs remain identifiable in the history.

## Proposed operator handoff

**Model 1** will produce a current concentration estimate for each incoming spectrum only when the spectral source, expected inputs, and target match a fitted calibration. The display should identify the source, target, and fitted model. A chemotools glucose calibration can supply glucose only. An unavailable compatible fit should leave that current estimate unavailable.

**Model 2** will use recent process observations to forecast ethanol at scheduled discharge. Its value should remain distinct from the current ethanol estimate and carry the forecast target, source, and fitted model. The synthetic replay illustrates a forecast issued at hour 30 for hour 36 against a 130 g/L target. Live plant integration is outside this iteration.

## Local checks

- Chrome confirmed the four sidebar links in order and Data Explorer at the root URL. Both NIR component tabs and the chemotools test view loaded.
- Chrome exercised source-range selection, confirmed a NIR configuration with the standardisation preview, and verified the handoff to training. It also confirmed a chemotools glucose configuration and ran its PLS/SVR preview.
- Chrome and Streamlit AppTest verified that switching to an unconfigured target or source hid the previous comparison’s active result and disabled its preview action. AppTest also verified individual NIR channel selection and the exact confirmed channel names.
- Chrome checked the synthetic shortfall forecast at 119.2 g/L, the lab reveal at hour 36 with a 120.4 g/L reference, and the transition to the on-target batch at 134.6 g/L with the previous lab result cleared.
- Python compilation passed. The local Streamlit health check returned `ok`.

## Files changed

- [app.py](app.py) reorganises navigation, configuration and comparison views, and the operator replay.
- [README.md](README.md) describes the new workflow and local entry point.
- This report records the implementation, verification, and preview boundaries.
