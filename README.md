# 🌾 SIH 2026 — Smart Panchayat Climate & Geospatial Intelligence Platform
**Domain:** Dhanbad District, Jharkhand, India (239 Panchayats, 10 Administrative Blocks)  
**Core Deliverables:** Multi-Source Environmental Datasets, High-Resolution Weather Downscaling ML Engine, Geospatial Intelligence Layers, and Decision-Support Dashboards.

---

## 📁 Repository Structure

```plaintext
SIH2026/
├── ml/                                 # Machine Learning Downscaling Engine & Experiments
│   ├── src/
│   │   ├── audit.py                    # Phase 1: Data audit & quality verification
│   │   ├── preprocessing.py            # Phase 2: Chronological Parquet dataset splitter
│   │   ├── features.py                 # Phase 3: Defensible feature engineering (no initial lags)
│   │   ├── baselines.py                # Phase 4: Baseline A (ERA5) & Baseline B (Climatology)
│   │   ├── train.py                    # Phase 5-7: Standardized Ridge, RF, XGBoost, LightGBM
│   │   ├── evaluate.py                 # Phase 8-9: Regression, contingency & GP metrics
│   │   ├── generalization.py           # Phase 10-11: Spatial holdout & validation permutation importance
│   │   └── visualization.py            # Phase 12: Publication-quality figure generation
│   ├── data/
│   │   └── processed/                  # Chronologically partitioned Parquet files
│   │       ├── train.parquet           # 2020-2022 Train (259,752 records)
│   │       ├── validation.parquet      # 2023 Validation (86,505 records)
│   │       └── test.parquet            # 2024 Test (86,742 records)
│   ├── results/                        # Complete experimental records, metrics & predictions
│   │   ├── experiment_metadata.json    # Machine-readable reproducibility configuration
│   │   ├── metrics_summary.csv         # Full model comparison matrix across all splits
│   │   ├── test_predictions.csv        # 2024 test predictions with residuals & errors (86,742 rows)
│   │   ├── panchayat_metrics.csv       # GP-level spatial evaluation across all 237 Panchayats
│   │   ├── spatial_generalization.csv  # Unseen block spatial holdout benchmark results
│   │   └── feature_importance.csv      # Validation set permutation importance rankings
│   ├── figures/                        # High-resolution publication visualizations (PNG format)
│   ├── run_pipeline.py                 # Master 12-phase pipeline orchestrator
│   ├── requirements.txt                # Python environment dependencies
│   └── README.md                       # Standalone ML pipeline documentation
├── models/                             # Serialized Model Checkpoints (.joblib)
│   ├── Ridge_residual.joblib           # Best performing Standardized Ridge Residual Downscaler
│   ├── Ridge_direct.joblib
│   ├── LightGBM_residual.joblib
│   ├── LightGBM_direct.joblib
│   ├── XGBoost_residual.joblib
│   ├── XGBoost_direct.joblib
│   ├── RandomForest_residual.joblib
│   └── RandomForest_direct.joblib
├── docs/                               # Research Documentation & Visual Assets
│   └── figures/                        # Core publication-ready PNG figures
│       ├── 1_baseline_vs_observed.png
│       ├── 2_model_vs_observed.png
│       ├── 3_error_distribution.png
│       ├── 4_monthly_monsoon_performance.png
│       ├── 5_feature_importance.png
│       └── 6_panchayat_error_distribution.png
├── data/                               # Static & Dynamic Datasets (Meteorological & Geospatial)
│   ├── dynamic/                        # Time-series datasets (2020–2024 daily records)
│   │   ├── Dhanbad_Panchayat_Rainfall_2020_2024.csv
│   │   ├── Dhanbad_Panchayat_Temperature_2020-24.csv
│   │   ├── et_2020-24.csv
│   │   ├── humidity_2020-24.csv
│   │   └── wind_2020-24.csv
│   ├── static/                         # Topographical & Land use baseline data
│   │   ├── Dhanbad_Panchayat_Elevation.csv
│   │   ├── Dhanbad_Panchayat_LandCover_2023.csv
│   │   ├── Dhanbad_Panchayat_LandCover_2023_Named.csv
│   │   └── Dhanbad_Panchayat_Slope.csv
│   └── README.md                       # Detailed data dictionary & merging guide
├── geo/                                # GIS boundary layers & GeoJSON files (.gitkeep)
├── notebooks/                          # Jupyter notebooks for exploratory data analysis (.gitkeep)
├── backend/                            # API server & real-time ingestion pipelines (.gitkeep)
├── frontend/                           # Interactive dashboard & GIS map views (.gitkeep)
├── .gitignore                          # Repository clean ignore definitions
└── README.md                           # Master Project README
```

---

## 🌟 Core Milestone Accomplished: Panchayat-Level Weather Downscaling

We have developed, calibrated, and benchmarked an end-to-end Machine Learning spatial downscaling engine that transforms coarse-resolution **ERA5-Land daily rainfall** (~9 km centroid-sampled) into localized, high-resolution **Panchayat-level daily rainfall (CHIRPS reference)** for **239 Panchayats** across Dhanbad district.

### 1. Mathematical Formulation
$$\text{RESIDUAL} = \text{RAINFALL}_{\text{Observed (CHIRPS)}} - \text{REFERENCE\_RAINFALL}_{\text{Coarse (ERA5-Land)}}$$
$$\widehat{\text{RESIDUAL}} = f_{\boldsymbol{\theta}}(\mathbf{x}_i)$$
$$\widehat{\text{RAINFALL}} = \max\left(0, \text{REFERENCE\_RAINFALL} + \widehat{\text{RESIDUAL}}\right)$$

### 2. Strict Chronological Validation Protocol
To eliminate temporal look-ahead leakage and simulate operational deployment:
* **Train Set:** `2020-01-01` to `2022-12-31` (3 years, 259,752 records)
* **Validation Set:** `2023-01-01` to `2023-12-31` (1 year, 86,505 records) — **used exclusively for model selection and validation permutation feature importance**.
* **Untouched Test Set:** `2024-01-01` to `2024-12-31` (1 year, 86,742 records) — **held strictly untouched until final benchmarking**.

---

## 📊 Key Benchmark Findings & Scientific Results

### 1. Performance on Untouched 2024 Test Set (86,742 Records)

| Model / Formulation | MAE (mm/day) | RMSE (mm/day) | $R^2$ Score | Pearson Correlation ($r$) | Key Takeaway |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Baseline A: Coarse ERA5 Reference** | 3.7500 | 10.2224 | -0.4250 | 0.5940 | High variance, systematic coarse bias |
| **Baseline B: Historical Climatology** | 4.5654 | 8.4695 | +0.0218 | 0.3754 | Captures only coarse seasonal mean |
| **Standardized Ridge Residual [BEST]** | **3.6738** | **6.6698** | **+0.3934** | **0.6434** | **-34.8% RMSE Reduction & +0.818 $R^2$ shift** |

### 2. Event Detection Contingency Metrics (2024 Test Set)

| Metric Threshold | Baseline A (Coarse ERA5) | Standardized Ridge Residual | Physical Dynamic |
| :--- | :---: | :---: | :--- |
| **Rain Event ($\ge 0.1\text{ mm}$)** | $\text{POD}=89.6\%, \text{CSI}=0.446$ | **$\text{POD}=98.6\%$**, $\text{CSI}=0.340$ | High detection; small drizzle false alarms |
| **Moderate Rain ($\ge 5.0\text{ mm}$)** | $\text{POD}=66.3\%, \text{CSI}=0.472$ | **$\text{POD}=79.7\%$**, $\text{CSI}=0.459$ | **Substantial boost in moderate rain capture** |
| **Heavy Rain ($\ge 15.0\text{ mm}$)** | $\text{POD}=40.9\%, \text{CSI}=0.323$ | $\text{POD}=33.9\%, \text{CSI}=0.279$ | Regression regularizes extreme peak spikes |

### 3. Spatial Generalization on Unseen Holdout Blocks

To verify that the model does not memorize Panchayat spatial identities, entire blocks (`Tundi` and `Topchanchi`, 42 Panchayats, 15,372 test records) were held out during training:
* **Unseen Holdout Blocks RMSE:** **$6.3920\text{ mm}$** (ML Model) vs **$8.9801\text{ mm}$** (ERA5 Reference Baseline) $\to$ **$+2.5881\text{ mm}$ (-28.8%) error reduction on unseen geography**.
* **Finding:** Confirms physical and meteorological transferability across geographic space.

### 4. Panchayat-Level Spatial Distribution (237 Panchayats)
* **Median Panchayat RMSE Reduction:** **$+3.5965\text{ mm/day}$**
* **25th / 75th Percentiles:** $+3.1630\text{ mm/day}$ / $+4.1169\text{ mm/day}$
* **Panchayats Improving over ERA5:** **100.0% (237 / 237 Panchayats)**

---

## 📈 Visualizations Catalog (`docs/figures/` & `ml/figures/`)

The pipeline generates 6 publication-ready figures tracking model performance:
1. `1_baseline_vs_observed.png` — Hexbin density comparison of ERA5-Land Reference vs CHIRPS (2024 Test Set).
2. `2_model_vs_observed.png` — Hexbin density comparison of Ridge Residual Downscaled vs CHIRPS (2024 Test Set).
3. `3_error_distribution.png` — Error probability density comparison showing sharp variance reduction and zero-centering.
4. `4_monthly_monsoon_performance.png` — Monthly seasonal rainfall tracking across the 2024 timeline.
5. `5_feature_importance.png` — Permutation feature importance evaluated strictly on the 2023 Validation Set.
6. `6_panchayat_error_distribution.png` — Spatial distribution of RMSE improvements across all 237 Panchayats.

---

## 📊 Dataset Catalog & Data Integration

The `data/` directory provides comprehensive environmental coverage across all Gram Panchayats in Dhanbad:

### 1. Dynamic Daily Time-Series (2020–2024)
| Dataset | Variable | Unit | Description | Key Join Columns |
| :--- | :--- | :--- | :--- | :--- |
| `Dhanbad_Panchayat_Rainfall_2020_2024.csv` | `RAINFALL_MM` | mm | Daily accumulated precipitation | `GPCODE`, `DATE` |
| `Dhanbad_Panchayat_Temperature_2020-24.csv` | `TEMPERATURE_C` | °C | Daily mean surface temperature | `GPCODE`, `DATE` |
| `et_2020-24.csv` | `ET_MM` | mm | Daily Evapotranspiration | `GPCODE`, `DATE` |
| `humidity_2020-24.csv` | `HUMIDITY_PERCENT` | % | Daily relative humidity percentage | `GPCODE`, `DATE` |
| `wind_2020-24.csv` | `WIND_SPEED_MS` | m/s | Daily average wind speed | `GPCODE`, `DATE` |

### 2. Static Terrain & Land Cover Features
| Dataset | Variable | Description | Key Join Columns |
| :--- | :--- | :--- | :--- |
| `Dhanbad_Panchayat_Elevation.csv` | `ELEVATION_M` | Mean elevation above sea level (meters) | `GPCODE` |
| `Dhanbad_Panchayat_Slope.csv` | `SLOPE_DEG` | Mean topographical slope (degrees) | `GPCODE` |
| `Dhanbad_Panchayat_LandCover_2023.csv` | `LANDCOVER_CLASS` | Numerical Land Cover Classification index | `GPCODE` |
| `Dhanbad_Panchayat_LandCover_2023_Named.csv` | `LANDCOVER_NAME` | Categorical land cover name (e.g. Croplands, Urban) | `GPCODE` |

---

## 🚀 Quickstart & Pipeline Reproduction

### 1. Environment Setup
```bash
cd ml
pip install -r requirements.txt
```

### 2. Run the Full ML Downscaling Pipeline
To run the complete 12-phase pipeline (data audit, chronological splitting, training, validation selection, test evaluation, spatial generalization, and visualization generation):
```bash
python3 run_pipeline.py
```

### 3. Load & Merge Environmental Data in Python
```python
import pandas as pd

# Load dynamic datasets
keys = ["GPCODE", "DATE"]
rainfall = pd.read_csv("../data/dynamic/Dhanbad_Panchayat_Rainfall_2020_2024.csv")
temp = pd.read_csv("../data/dynamic/Dhanbad_Panchayat_Temperature_2020-24.csv")
et = pd.read_csv("../data/dynamic/et_2020-24.csv")
humidity = pd.read_csv("../data/dynamic/humidity_2020-24.csv")
wind = pd.read_csv("../data/dynamic/wind_2020-24.csv")

dynamic_df = (
    rainfall[["GPCODE", "GPNAME", "DATE", "RAINFALL_MM"]]
    .merge(temp[["GPCODE", "DATE", "TEMPERATURE_C"]], on=keys, how="inner")
    .merge(et[["GPCODE", "DATE", "ET_MM"]], on=keys, how="inner")
    .merge(humidity[["GPCODE", "DATE", "HUMIDITY_PERCENT"]], on=keys, how="inner")
    .merge(wind[["GPCODE", "DATE", "WIND_SPEED_MS"]], on=keys, how="inner")
)

# Load static terrain datasets
elevation = pd.read_csv("../data/static/Dhanbad_Panchayat_Elevation.csv")[["GPCODE", "ELEVATION_M"]]
slope = pd.read_csv("../data/static/Dhanbad_Panchayat_Slope.csv")[["GPCODE", "SLOPE_DEG"]]
landcover = pd.read_csv("../data/static/Dhanbad_Panchayat_LandCover_2023_Named.csv")[["GPCODE", "LANDCOVER_CLASS", "LANDCOVER_NAME"]]

static_df = elevation.merge(slope, on="GPCODE").merge(landcover, on="GPCODE")
master_df = dynamic_df.merge(static_df, on="GPCODE", how="left")
print(f"Master Dataset Shape: {master_df.shape}")
```

---

## 📌 Project Milestones Status

- [x] **Milestone 1:** Dynamic and static environmental data extraction and standardization (`data/`).
- [x] **Milestone 2:** Panchayat-level weather downscaling ML pipeline with chronological validation (`ml/`).
- [x] **Milestone 3:** Standardized residual correction modeling, diagnostics, and spatial holdout experiments (`models/`).
- [x] **Milestone 4:** Full publication visualizations, metrics tables, and metadata serialization (`docs/` & `ml/results/`).
- [ ] **Milestone 5:** FastAPI backend deployment for real-time Panchayat advisory inference (`backend/`).
- [ ] **Milestone 6:** Interactive frontend dashboard with GIS Panchayat map views (`frontend/`).

---

## 👥 Team Collaboration Guidelines

1. **Branching Strategy:** Use descriptive feature branches (`feature/<component-name>`) and open pull requests against `main`.
2. **Reproducibility:** When training models or updating pipelines, ensure fixed random seeds (`random_state=42`) and save experiment metadata under `ml/results/`.
3. **Large Files:** Preprocessed parquet splits and serialized models are versioned; avoid committing transient logs or `.DS_Store` files.
