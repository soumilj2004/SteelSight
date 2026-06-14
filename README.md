# SteelSight — Satellite Commodity Intelligence Platform

> A remote sensing and machine learning pipeline that derives quantitative operational activity signals from Sentinel-2 SWIR imagery across 45 Chinese steel manufacturing facilities, demonstrating a statistically significant 2-month leading indicator over World Steel Association monthly output reports.

![Dashboard Preview](screenshots/dashboard_overview.png)

---

## The Story in One Paragraph

Chinese steel mills running at full capacity emit distinctive heat signatures in shortwave infrared wavelengths, visible from space. By processing 2,815 monthly Sentinel-2 satellite image composites across 45 major Chinese steel facilities and computing a spatially-normalised SWIR heat index, SteelSight generates a monthly signal representing the percentage of monitored facilities actively operating. This signal demonstrates a statistically significant negative lead correlation with WSA crude steel output at a 2-month lag (R²=0.173, p=0.0003). Iron ore prices fell 56% in the 10 weeks following the peak signal reading in August 2021 — a move our satellite data indicated 8 weeks before the price peak.

---

## Results

| Metric | Value |
|---|---|
| Facilities monitored | 45 Chinese steel mills |
| Images processed | 2,815 monthly composites |
| Observation window | January 2019 — December 2024 |
| Optimal signal lag | 2 months |
| R² (signal vs WSA output) | 0.173 |
| Pearson r | −0.416 |
| p-value | 0.0003 |
| Iron ore price lead | ~8 weeks (Aug 2021 episode) |

---

## Dashboard

![Signal vs Production](screenshots/signal_chart.png)

*Monthly SWIR activity signal (gold) overlaid against WSA crude steel output (blue dashed).*

![Commodity Prices](screenshots/commodity_chart.png)

*Iron ore and HRC steel price history. Note the sharp iron ore collapse in Q3–Q4 2021.*

![Facility Map](screenshots/facility_map.png)

*45 monitored facilities. Dot size proportional to SWIR heat score.*

![Narrative Summary](screenshots/narrative_summary.png)

*End-to-end narrative: signal fired → output dropped → iron ore fell.*

---

## Architecture

```
Google Earth Engine (Sentinel-2 SR)
        ↓
Monthly median composites — 45 mills × 72 months
        ↓
SWIR Heat Index (B11 + B12, z-score normalised)
        ↓
Per-facility activity scores → monthly aggregate signal
        ↓
Cross-lag Pearson correlation vs WSA output
        ↓
Financial validation vs iron ore + HRC futures
        ↓
FastAPI backend + React dashboard
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Satellite data | Sentinel-2 SR via Google Earth Engine |
| Image processing | Rasterio, NumPy, OpenCV |
| Signal computation | Custom SWIR heat index (no labeling required) |
| Correlation analysis | SciPy, Pandas, Statsmodels |
| Backend | FastAPI, Uvicorn |
| Frontend | React, Recharts, Vite |
| Annotation tool | Custom-built (label_tool.py) |

---

## Methodology

### SWIR Heat Index

The per-pixel SWIR composite `S(i,j)` is the mean of the two heat-sensitive bands:

```
S(i,j) = [ B11(i,j) + B12(i,j) ] / 2
```

Spatial z-score normalises for atmospheric and seasonal variation:

```
z(i,j) = [ S(i,j) − μ_S ] / σ_S
```

Pixels with `z > 2.0` are thermal anomalies. Per-facility monthly heat score:

```
H_t = (N_anomaly / N_valid) × (μ_anomaly / μ_S)
```

The aggregate monthly signal `A_t` is the percentage of facilities exceeding an adaptive 35th-percentile threshold.

### Why the Correlation is Negative

The negative correlation (high activity → lower subsequent output) reflects documented Chinese steel production cycle dynamics: elevated mill activity creates pollution events that trigger government-mandated curtailments. The satellite signal detects the cause; the WSA report measures the effect.

---

## Project Structure

```
steelmill/
├── data/
│   ├── mills.csv                    45 mill coordinates
│   ├── activity_scores.csv          Per-mill monthly heat scores
│   ├── monthly_signal.csv           Aggregate monthly signal
│   ├── wsa_steel_output.csv         WSA ground truth data
│   └── financial/                   Iron ore + HRC price data
├── src/
│   ├── data_pipeline/
│   │   ├── download_gee.py          Sentinel-2 image download
│   │   └── preprocess.py            GeoTIFF to PNG chips
│   ├── inference/
│   │   └── swir_heat_index.py       Core SWIR heat index pipeline
│   ├── analysis/
│   │   └── correlation_analysis.py  WSA correlation + plots
│   ├── financial/
│   │   └── fetch_prices.py          Iron ore + HRC price data
│   └── api/
│       └── api.py                   FastAPI backend
├── frontend/
│   └── src/
│       └── App.jsx                  React dashboard
├── label_tool.py                    Custom annotation interface
├── run.py                           One-command launcher
└── SteelSight_IEEE_Paper.pdf        Research paper
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 22+
- Google Earth Engine account — [register here](https://earthengine.google.com) (free)

### Install

```bash
git clone https://github.com/YOUR_USERNAME/steelsight.git
cd steelsight
pip install -r requirements.txt
```

### Authenticate GEE

```bash
earthengine authenticate
```

### Download satellite imagery

```bash
python src/data_pipeline/download_gee.py
```

*Downloads ~9GB across 45 mills from 2019–2024. Takes 4–6 hours.*

### Run the SWIR pipeline

```bash
python src/inference/swir_heat_index.py
```

### Run correlation analysis

```bash
python src/analysis/correlation_analysis.py
```

### Launch the dashboard

```bash
python run.py
```

*Opens automatically at http://localhost:5173*

---

## Annotation Tool

Custom browser-based annotation interface — no external platform required.

![Annotation Tool](screenshots/annotation_tool.png)

```bash
python label_tool.py
# Opens at http://localhost:9000
```

Keyboard shortcuts: `A` = Active · `I` = Idle · `S` = Skip. Auto-saves and auto-advances.

---

## Research Paper

📄 **[SteelSight_IEEE_Paper.pdf](SteelSight_IEEE_Paper.pdf)**

*SteelSight: Satellite-Derived SWIR Heat Indices for Predicting Chinese Crude Steel Output and Commodity Price Dynamics*

IEEE format. Covers full methodology, statistical results, interpretation of the negative correlation, limitations, and future work.

---

## Key Finding — The August 2021 Episode

The clearest illustration of the signal working in practice:

- **Aug 2021:** Satellite signal peaks at 91.9% of mills active — all-time high
- **Oct 2021:** WSA reports 14% output drop as Beijing enforces production curtailments
- **Sep–Nov 2021:** Iron ore falls from $218/t to $96/t — a 56% collapse in 10 weeks
- **Lead time:** Our signal indicated this 8 weeks before the price peak

The mechanism is coherent and independently documented:

```
Peak SWIR activity → visible pollution → regulatory response → output curtailment → demand destruction → iron ore price fall
```

---

## Limitations

- 3km chip size captures surrounding urban area alongside the facility
- Sentinel-2 SWIR is reflectance, not true thermal infrared
- Cloud cover removes ~15–20% of monthly observations
- R²=0.17 explains ~17% of variance — a leading indicator, not a price predictor

---

## Future Work

- Landsat-8/9 TIRS thermal infrared for true temperature measurement
- AIS ship tracking from nearby ports as a corroborating signal
- Expansion to India, Japan, South Korea for global production coverage
- Vision Transformer fine-tuning for facility-level classification

---

## Data Sources

| Source | Data | Access |
|---|---|---|
| ESA Copernicus / Google Earth Engine | Sentinel-2 SR imagery | Free |
| World Steel Association | Monthly crude steel output | Free |
| World Bank Commodity Data | Iron ore 62% Fe CFR China | Public |
| CME Group | HRC steel futures | Public |

---

## License

MIT — see [LICENSE](LICENSE)

---

*Built by Soumil Jain · PES University, Bengaluru*
