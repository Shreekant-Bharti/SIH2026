# Data Quality & Audit Report: Dhanbad Rainfall Downscaling

- **Source File:** `master_dataset_v2.csv` (Raw file strictly unmodified)
- **Total Rows:** 436,653
- **Total Columns:** 13
- **Date Coverage:** 2020-01-01 to 2024-12-31 (1827 continuous days)
- **Panchayats (GPCODEs):** 239 across 10 Administrative Blocks
- **Duplicate (DATE, GPCODE) pairs:** 0
- **ERA5-Land Reference Rainfall Presence:** Confirmed (`REFERENCE_RAINFALL` present with 0 missing values)

## Missing Target Analysis (`RAINFALL`)

Total missing target rows: **3,654** (0.84% of total dataset).

These missing rows belong entirely to **2 Panchayats** across the full 5-year timeline:

- **GPCODE `111755`**: `MAHESHPUR 2` (Block: `Baghmara`) — 1,827 missing target rows
- **GPCODE `111773`**: `RAJGANJ` (Block: `Baghmara`) — 1,827 missing target rows

*Note:* For both of these Panchayats, all meteorological and terrain features are 100% complete. In accordance with Phase 2 protocol, these rows are excluded from model training/evaluation while preserving raw dataset integrity.

## Feature Properties & Units

| Feature | Physical Meaning | Unit / Type | Completeness |
| :--- | :--- | :--- | :--- |
| `RAINFALL` | Observed Panchayat Precipitation (CHIRPS) | mm/day | 99.16% (3,654 missing) |
| `REFERENCE_RAINFALL` | Coarse ERA5-Land Centroid Precipitation | mm/day | 100.0% |
| `TEMPERATURE` | 2m Air Temperature | °C | 100.0% |
| `HUMIDITY` | Relative / Specific Humidity | % | 100.0% |
| `WIND` | 10m Wind Speed | m/s | 100.0% |
| `ET` | Daily Evapotranspiration | mm/day | 100.0% |
| `ELEVATION` | Surface Elevation above sea level | meters | 100.0% |
| `SLOPE` | Terrain Slope | degrees | 100.0% |
| `LANDCOVER` | Land Cover Classification Code | Discrete Category | 100.0% |

## Distribution & Skewness Check

- **CHIRPS Dry Days (<0.1 mm):** 70.94%
- **ERA5-Land Dry Days (<0.1 mm):** 48.02%
- **CHIRPS Max Daily Rainfall:** 125.26 mm/day
- **ERA5-Land Max Daily Rainfall:** 204.96 mm/day
