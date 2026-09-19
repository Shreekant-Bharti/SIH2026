# 🌾 SIH 2026 — Smart Panchayat Climate & Geospatial Intelligence Platform

Welcome to the **SIH 2026** project repository! This repository contains the complete end-to-end codebase, datasets, geospatial layers, machine learning pipelines, and application interfaces for Panchayat-level environmental, meteorological, and terrain intelligence for Dhanbad district.

---

## 📁 Repository Structure

```plaintext
SIH2026/
├── data/                  # Static & dynamic datasets (Meteorological & Geospatial)
│   ├── dynamic/           # Time-series datasets (2020–2024 daily records)
│   │   ├── Dhanbad_Panchayat_Rainfall_2020_2024.csv
│   │   ├── Dhanbad_Panchayat_Temperature_2020-24.csv
│   │   ├── et_2020-24.csv
│   │   ├── humidity_2020-24.csv
│   │   └── wind_2020-24.csv
│   ├── static/            # Topographical & Land use baseline data
│   │   ├── Dhanbad_Panchayat_Elevation.csv
│   │   ├── Dhanbad_Panchayat_LandCover_2023.csv
│   │   ├── Dhanbad_Panchayat_LandCover_2023_Named.csv
│   │   └── Dhanbad_Panchayat_Slope.csv
│   └── README.md          # Detailed data dictionary & merging guide
├── geo/                   # GIS layers, boundary shapefiles, and GeoJSON files
├── notebooks/             # Jupyter notebooks for EDA, preprocessing & experiments
├── ml/                    # Machine learning models, feature engineering & training scripts
├── models/                # Serialized model checkpoints, scalers & weights
├── backend/               # Backend API server & data ingestion pipelines
├── frontend/              # Web application, interactive dashboard & GIS map views
└── docs/                  # Architecture diagrams, research documentation & API specs
```

---

## 📊 Dataset Catalog

The data directory provides comprehensive coverage across all Gram Panchayats in Dhanbad across multiple environmental variables:

### 1. Dynamic Daily Time-Series (2020 – 2024)
| Dataset | Variable | Unit | Description | Key Join Columns |
| :--- | :--- | :--- | :--- | :--- |
| `Dhanbad_Panchayat_Rainfall_2020_2024.csv` | `RAINFALL_MM` | mm | Daily accumulated precipitation | `GPCODE`, `DATE` |
| `Dhanbad_Panchayat_Temperature_2020-24.csv` | `TEMPERATURE_C` | °C | Daily mean surface temperature | `GPCODE`, `DATE` |
| `et_2020-24.csv` | `ET_MM` | mm | Daily Evapotranspiration | `GPCODE`, `DATE` |
| `humidity_2020-24.csv` | `HUMIDITY_PERCENT`| % | Daily relative humidity percentage | `GPCODE`, `DATE` |
| `wind_2020-24.csv` | `WIND_SPEED_MS` | m/s | Daily average wind speed | `GPCODE`, `DATE` |

### 2. Static Terrain & Land Cover Features
| Dataset | Variable | Description | Key Join Columns |
| :--- | :--- | :--- | :--- |
| `Dhanbad_Panchayat_Elevation.csv` | `ELEVATION_M` | Mean elevation above sea level (meters) | `GPCODE` |
| `Dhanbad_Panchayat_Slope.csv` | `SLOPE_DEG` | Mean topographical slope (degrees) | `GPCODE` |
| `Dhanbad_Panchayat_LandCover_2023.csv` | `LANDCOVER_CLASS`| Numerical Land Cover Classification index | `GPCODE` |
| `Dhanbad_Panchayat_LandCover_2023_Named.csv` | `LANDCOVER_NAME` | Categorical land cover name (e.g. Croplands, Urban) | `GPCODE` |

---

## 🚀 Quick Start — Loading & Merging Data

For team members working on ML, analytics, or backend services, here is a quick Python snippet to merge the dynamic and static features into a unified dataframe:

```python
import pandas as pd

# 1. Load Dynamic Datasets
rainfall = pd.read_csv("data/dynamic/Dhanbad_Panchayat_Rainfall_2020_2024.csv")
temp = pd.read_csv("data/dynamic/Dhanbad_Panchayat_Temperature_2020-24.csv")
et = pd.read_csv("data/dynamic/et_2020-24.csv")
humidity = pd.read_csv("data/dynamic/humidity_2020-24.csv")
wind = pd.read_csv("data/dynamic/wind_2020-24.csv")

# Standardize column selections
keys = ["GPCODE", "DATE"]
dynamic_df = (
    rainfall[["GPCODE", "GPNAME", "DATE", "RAINFALL_MM"]]
    .merge(temp[["GPCODE", "DATE", "TEMPERATURE_C"]], on=keys, how="inner")
    .merge(et[["GPCODE", "DATE", "ET_MM"]], on=keys, how="inner")
    .merge(humidity[["GPCODE", "DATE", "HUMIDITY_PERCENT"]], on=keys, how="inner")
    .merge(wind[["GPCODE", "DATE", "WIND_SPEED_MS"]], on=keys, how="inner")
)

# 2. Load Static Datasets
elevation = pd.read_csv("data/static/Dhanbad_Panchayat_Elevation.csv")[["GPCODE", "ELEVATION_M"]]
slope = pd.read_csv("data/static/Dhanbad_Panchayat_Slope.csv")[["GPCODE", "SLOPE_DEG"]]
landcover = pd.read_csv("data/static/Dhanbad_Panchayat_LandCover_2023_Named.csv")[["GPCODE", "LANDCOVER_CLASS", "LANDCOVER_NAME"]]

static_df = elevation.merge(slope, on="GPCODE").merge(landcover, on="GPCODE")

# 3. Master Combined Dataset
master_df = dynamic_df.merge(static_df, on="GPCODE", how="left")
print(f"Master Dataset Shape: {master_df.shape}")
print(master_df.head())
```

---

## 👥 Team Workflow Guidelines

To ensure smooth collaboration:
1. **Branching**: Create feature branches (`git checkout -b feature/<feature-name>`) for substantial new work and open pull requests against `main`.
2. **Data & Large Files**: Keep cleaned, shared raw data in `data/`. Avoid pushing temporary intermediate cache files.
3. **Commit Messages**: Write clear, descriptive commit messages specifying what component was updated (e.g. `feat(ml): add XGBoost baseline model`).

---

## 📌 Project Milestones
- [x] Dataset extraction, consolidation & formatting (Dynamic 2020-2024 + Static terrain)
- [ ] Exploratory Data Analysis & baseline correlation studies (`notebooks/`)
- [ ] Predictive Modeling & Validation Pipeline (`ml/` & `models/`)
- [ ] FastAPI / Flask backend service development (`backend/`)
- [ ] Frontend interactive map & analytics dashboard (`frontend/`)