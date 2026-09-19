# 📂 Dhanbad Panchayat Datasets Guide

This directory contains meteorological dynamic time-series (2020–2024) and static topographical/land cover datasets covering all Gram Panchayats in Dhanbad district.

---

## 🕒 Dynamic Data (`data/dynamic/`)

All files in this folder contain daily aggregated records spanning **2020-01-01** through **2024-12-31**.

| File Name | Primary Metric | Type | Unit | Join Keys |
| :--- | :--- | :--- | :--- | :--- |
| `Dhanbad_Panchayat_Rainfall_2020_2024.csv` | `RAINFALL_MM` | Float | mm | `GPCODE`, `DATE` |
| `Dhanbad_Panchayat_Temperature_2020-24.csv` | `TEMPERATURE_C` | Float | °C | `GPCODE`, `DATE` |
| `et_2020-24.csv` | `ET_MM` | Float | mm | `GPCODE`, `DATE` |
| `humidity_2020-24.csv` | `HUMIDITY_PERCENT` | Float | % | `GPCODE`, `DATE` |
| `wind_2020-24.csv` | `WIND_SPEED_MS` | Float | m/s | `GPCODE`, `DATE` |

### Key Fields:
- **`GPCODE`**: Unique Gram Panchayat code identifier (e.g. `111722`).
- **`GPNAME`**: Gram Panchayat name (e.g. `BAGDAHA`, `BAGRA`).
- **`BLOCK`**: Sub-district administrative block (e.g. `Baghmara`).
- **`DATE`**: Daily timestamp formatted as `YYYY-MM-DD`.

---

## ⛰️ Static Data (`data/static/`)

Baseline topographical and land use/land cover attributes at the Panchayat level:

| File Name | Primary Attribute | Type | Description | Join Keys |
| :--- | :--- | :--- | :--- | :--- |
| `Dhanbad_Panchayat_Elevation.csv` | `ELEVATION_M` | Float/Int | Mean elevation in meters above sea level | `GPCODE` |
| `Dhanbad_Panchayat_Slope.csv` | `SLOPE_DEG` | Float | Mean terrain slope angle in degrees | `GPCODE` |
| `Dhanbad_Panchayat_LandCover_2023.csv` | `LANDCOVER_CLASS` | Integer | Land Cover Classification code (2023) | `GPCODE` |
| `Dhanbad_Panchayat_LandCover_2023_Named.csv` | `LANDCOVER_NAME` | String | Readable class name (e.g., Croplands, Urban) | `GPCODE` |

---

## 🔗 Combining Data for Machine Learning

```python
import pandas as pd

# Load dynamic files
rain = pd.read_csv("data/dynamic/Dhanbad_Panchayat_Rainfall_2020_2024.csv")
temp = pd.read_csv("data/dynamic/Dhanbad_Panchayat_Temperature_2020-24.csv")
et = pd.read_csv("data/dynamic/et_2020-24.csv")
hum = pd.read_csv("data/dynamic/humidity_2020-24.csv")
wind = pd.read_csv("data/dynamic/wind_2020-24.csv")

# Merge dynamic time series on GPCODE and DATE
dynamic = (
    rain[["GPCODE", "GPNAME", "DATE", "RAINFALL_MM"]]
    .merge(temp[["GPCODE", "DATE", "TEMPERATURE_C"]], on=["GPCODE", "DATE"])
    .merge(et[["GPCODE", "DATE", "ET_MM"]], on=["GPCODE", "DATE"])
    .merge(hum[["GPCODE", "DATE", "HUMIDITY_PERCENT"]], on=["GPCODE", "DATE"])
    .merge(wind[["GPCODE", "DATE", "WIND_SPEED_MS"]], on=["GPCODE", "DATE"])
)

# Load static files
elev = pd.read_csv("data/static/Dhanbad_Panchayat_Elevation.csv")[["GPCODE", "ELEVATION_M"]]
slope = pd.read_csv("data/static/Dhanbad_Panchayat_Slope.csv")[["GPCODE", "SLOPE_DEG"]]
lc = pd.read_csv("data/static/Dhanbad_Panchayat_LandCover_2023_Named.csv")[["GPCODE", "LANDCOVER_CLASS", "LANDCOVER_NAME"]]

static = elev.merge(slope, on="GPCODE").merge(lc, on="GPCODE")

# Complete merged dataset
final_df = dynamic.merge(static, on="GPCODE", how="left")
```
