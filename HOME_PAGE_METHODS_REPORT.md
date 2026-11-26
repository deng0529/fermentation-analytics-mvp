# Fermentation Analytics Home page

26 November 2026 · [Open the local app](http://127.0.0.1:8506/)

Home opens at the root URL. It introduces the app, shows the three modelling tasks with their fitted methods, and links to the four modules. The workflow explains that Model 1 ethanol estimates can feed Ridge when replay supplies a compatible batch history and discharge schedule. Synthetic ethanol readings can feed Ridge directly.

The workspace copy previously opened Data Explorer at the root and contained no Streamlit Home renderer. The update adds a native Streamlit workflow and cards, and registers Data Explorer at `/data-explorer`. The other three module URLs retain their existing paths.

## Navigation checks

Headless Chrome opened a new session at `/` and verified the **Fermentation Analytics** heading and Home sidebar entry. Each Home link received keyboard focus and opened the expected page when activated with Enter. The browser checked the resulting URL and page heading.

| Home link | Verified destination |
| --- | --- |
| Data Explorer | `/data-explorer` |
| Preprocessing & Feature Selection | `/preprocessing` |
| Model Training & Validation | `/training` |
| Batch Monitor | `/batch-monitor` |
| Estimate current ethanol | `/training` |
| Estimate current glucose | `/training` |
| Forecast ethanol at discharge | `/batch-monitor` |

## Layout checks

At 1,440 px, the calibration boxes appeared side by side and the module cards formed a two-column grid. At 768, 390, and 320 px, all seven boxes stayed within the viewport without clipped link or paragraph text. At 390 and 320 px, the boxes stacked in a single column. The Home page used the existing light theme throughout.

All requested checks completed in local headless Chrome. Other browser engines and physical mobile devices were outside the verification scope.

## Files changed

- `app.py` adds the Home renderer and updates the existing Streamlit navigation so Home is the default.
- `HOME_PAGE_METHODS_REPORT.md` records the change and verification.
