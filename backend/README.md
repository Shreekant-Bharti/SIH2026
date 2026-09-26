# SIH2026 FastAPI Backend & Model Serving

Production-grade FastAPI serving layer for the SIH2026 localized Panchayat rainfall downscaling system.

---

## 1. System Overview & Architecture

The backend bridges the user interface with the trained machine learning pipeline. It loads the frozen `Ridge_residual.joblib` pipeline and strictly reuses canonical feature engineering logic (`ml/src/features.py`) to prevent train/serve skew.

```
                    ┌────────────────────────┐
                    │      React Frontend    │
                    │   (e.g. localhost:5173)│
                    └───────────┬────────────┘
                                │
                          REST / JSON
                                │
                                ▼
                    ┌────────────────────────┐
                    │     FastAPI Backend    │
                    │   (e.g. localhost:8000)│
                    └───────────┬────────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       │                        │                        │
       ▼                        ▼                        ▼
Administrative / Geo      Historical Data           ML Pipeline
  - Districts               - 2024 Test Predictions   - StandardScaler
  - Blocks                  - Evaluated Baselines     - Ridge(alpha=10.0)
  - Panchayats                                           │
  - Terrain Features                                     ▼
                                                 Predicted Residual
                                                         │
                                                         ▼
                                               Reconstructed Rainfall
                                              max(Ref + Residual, 0)
```

### Critical Architectural Disclaimer: Reanalysis vs Real-Time NWP

- **Current Operational Scope**: The model is trained on **ERA5-Land reanalysis meteorological data** and evaluated on localized IMD/gauge targets.
- **Demonstrated Capability**: The current MVP serves **validated Panchayat-level spatial rainfall downscaling**.
- **Real-Time Forecast Precondition**: Real-time forward-looking forecasting requires operational Numerical Weather Prediction (NWP) inputs (e.g. IMD WRF/GFS or ECMWF IFS feeds) rather than ERA5-Land historical reanalysis. The system does not fabricate future forecasts without appropriate operational weather inputs.

---

## 2. Directory Structure

```
backend/
├── main.py                     # FastAPI application definition and routing
├── requirements.txt            # Python dependencies
├── README.md                   # Backend documentation and usage guide
│
├── services/
│   ├── __init__.py
│   ├── model_service.py        # Ridge Residual model loading and inference
│   └── data_service.py         # Administrative lookup and historical data
│
├── schemas/
│   ├── __init__.py
│   └── prediction.py           # Pydantic data schemas and validation rules
│
└── tests/
    ├── test_health.py          # Health check and model metadata tests
    └── test_prediction.py      # Endpoints, prediction sanity, and error tests
```

---

## 3. Installation & Setup

### Prerequisites

- Python 3.10+ (Tested on Python 3.13)
- Virtual environment (recommended)

### Installation

From the repository root or backend directory:

```bash
pip install -r backend/requirements.txt
```

---

## 4. Running the Application

### Development Server

Run from the repository root:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Or from within the `backend/` directory:

```bash
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Interactive API Documentation (Swagger)

Once the server is running, visit:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 5. API Reference & Examples

### System & Health Endpoints

#### `GET /health`

Verifies API status and model artifact loading. Fails closed (reports `"status": "error"`, `"model_loaded": false`) if the model file is missing or damaged.

**Response (200 OK):**

```json
{
  "status": "ok",
  "model_loaded": true,
  "model": "Ridge_Residual",
  "model_version": "Ridge_Residual_v1"
}
```

#### `GET /model/info`

Returns model specifications, version tag, and expected feature count.

**Response (200 OK):**

```json
{
  "model": "Ridge_Residual",
  "version": "Ridge_Residual_v1",
  "target": "Panchayat-level rainfall",
  "prediction_type": "Residual downscaling",
  "feature_count": 15,
  "status": "loaded"
}
```

---

### Administrative Geography Endpoints

#### `GET /districts`

Returns covered districts. (Current MVP scope: Dhanbad, Jharkhand).

**Response (200 OK):**

```json
{
  "districts": [
    {
      "name": "Dhanbad",
      "state": "Jharkhand"
    }
  ]
}
```

#### `GET /blocks?district=Dhanbad`

Returns all administrative blocks for a district.

**Response (200 OK):**

```json
{
  "district": "Dhanbad",
  "blocks": [
    "Baghmara",
    "Baliapur",
    "Dhanbad",
    "Egarkund",
    "Govindpur",
    "Kaliasol",
    "Nirsa",
    "Purvi Tundi",
    "Topchanchi",
    "Tundi"
  ]
}
```

#### `GET /panchayats?block=Baghmara`

Returns all Panchayats in a block with their unique Local Government Directory `gpcode`.

**Response (200 OK):**

```json
{
  "block": "Baghmara",
  "panchayats": [
    {
      "gpcode": 111722,
      "name": "BAGDAHA"
    },
    {
      "gpcode": 111755,
      "name": "MAHESHPUR 2"
    },
    {
      "gpcode": 111773,
      "name": "RAJGANJ"
    }
  ]
}
```

#### `GET /panchayat/{gpcode}`

Returns static topographic and land classification parameters for a Panchayat.

**Example Request:**
`GET /panchayat/111755`

**Response (200 OK):**

```json
{
  "gpcode": 111755,
  "name": "MAHESHPUR 2",
  "block": "Baghmara",
  "district": "Dhanbad",
  "elevation": 237.0,
  "slope": 1.37,
  "landcover": 12
}
```

---

### Prediction Input Retrieval

#### `GET /input/{gpcode}?date=YYYY-MM-DD`

Returns model inputs from `ml/data/raw/master_dataset_v2.csv`. The caller supplies only a Panchayat GPCODE and a date; the API does not impute missing fields or observations.

**Example:** `GET /input/111722?date=2024-07-15`

**Response (200 OK):**

```json
{
  "gpcode": 111722,
  "date": "2024-07-15",
  "temperature": 28.25112876892092,
  "humidity": 82.89589920431774,
  "wind": 3.2809103445880776,
  "et": 3.886740654706955,
  "elevation": 249.0,
  "slope": 3.5588596,
  "landcover": 12,
  "reference_rainfall": 2.8233021497676702,
  "observed_rainfall_mm": 10.15231953897784
}
```

For `MAHESHPUR 2` and `RAJGANJ`, `observed_rainfall_mm` is `null`; all prediction inputs remain sourced from the master dataset. Unknown Panchayats and dates return 404, malformed dates return 400, and missing model inputs return 422.

---

### Core Inference Endpoint

#### `POST /predict`

Performs localized downscaled rainfall estimation.

**Model Pipeline Contract:**

1. Validates inputs: `landcover` must be in `{4, 10, 12, 13}`, `date` must be valid `YYYY-MM-DD`.
2. Computes the 15 canonical features via `ml.src.features.extract_features`:
   - Meteorological: `TEMPERATURE`, `HUMIDITY`, `WIND`, `ET`
   - Spatial/Orographic: `ELEVATION`, `SLOPE`, `LANDCOVER`
   - Temporal: `MONTH`, `DAY_OF_YEAR`, `SIN_DOY`, `COS_DOY`, `MONSOON_FLAG`
   - Baseline properties: `REFERENCE_RAINFALL`, `LOG_REFERENCE_RAINFALL`, `REFERENCE_RAIN_EVENT`
3. Pipeline evaluates residual: `predicted_residual = model.predict(X)`
4. Reconstructs localized rainfall: `predicted_rainfall = max(REFERENCE_RAINFALL + predicted_residual, 0)`

**Request Payload:**

```json
{
  "gpcode": 111722,
  "date": "2024-07-15",
  "temperature": 28.25112876892092,
  "humidity": 82.89589920431774,
  "wind": 3.2809103445880776,
  "et": 3.886740654706955,
  "elevation": 249.0,
  "slope": 3.5588596,
  "landcover": 12,
  "reference_rainfall": 2.8233021497676702
}
```

**Response (200 OK):**

```json
{
  "gpcode": 111722,
  "date": "2024-07-15",
  "predicted_rainfall_mm": 6.32,
  "reference_rainfall_mm": 2.82,
  "model": "Ridge_Residual",
  "model_version": "Ridge_Residual_v1"
}
```

---

### Historical & Validation Endpoints

#### `GET /history/{gpcode}?start_date=2024-07-01&end_date=2024-07-05`

Returns daily time series for historical trend visualization.

**Response (200 OK for standard Panchayat):**

```json
{
  "gpcode": 111722,
  "data": [
    {
      "date": "2024-07-01",
      "observed_rainfall_mm": 23.35,
      "reference_rainfall_mm": 14.06,
      "predicted_rainfall_mm": 12.82
    }
  ]
}
```

**Response (200 OK for MAHESHPUR 2 / RAJGANJ):**

> Observed rainfall is strictly `null` because observed ground-truth records are missing for these Panchayats in the dataset. Predictions and reference data are grounded in real ERA5 records.

```json
{
  "gpcode": 111755,
  "data": [
    {
      "date": "2024-07-01",
      "observed_rainfall_mm": null,
      "reference_rainfall_mm": 13.23,
      "predicted_rainfall_mm": 12.44
    }
  ]
}
```

#### `GET /validation/{gpcode}`

Returns empirical model validation metrics (evaluated over the 2024 hold-out test set).

**Response (200 OK):**

```json
{
  "gpcode": 111722,
  "rmse": 6.06,
  "mae": 3.38,
  "r2": 0.4,
  "bias": 0.98,
  "correlation": 0.66,
  "baseline_rmse": 9.72,
  "baseline_mae": 3.38,
  "model_rmse": 6.06
}
```

If the requested Panchayat has no valid observed target (e.g. `111755` MAHESHPUR 2):

```json
{
  "detail": "Validation metrics unavailable for GPCODE 111755: observed ground-truth rainfall records are unavailable."
}
```

---

## 6. Error Handling

| Scenario                         | HTTP Status                | Behavior                                                                   |
| :------------------------------- | :------------------------- | :------------------------------------------------------------------------- |
| Model file missing or corrupted  | `503 Service Unavailable`  | Model fails closed. Never produces dummy or random numbers.                |
| Invalid Landcover code (e.g. 99) | `400 Bad Request`          | Returns clear validation error detailing allowed codes: `[4, 10, 12, 13]`. |
| Invalid Date format (e.g. "abc") | `400 Bad Request`          | Returns validation error requiring `YYYY-MM-DD`.                           |
| Missing required input fields    | `422 Unprocessable Entity` | Pydantic validation error detailing missing attributes.                    |
| Negative reference rainfall      | `200 OK`                   | Automatically clipped to `0.0` per model contract.                         |
| Unknown Panchayat GPCODE         | `404 Not Found`            | Returns descriptive error message.                                         |
| Unknown Administrative Block     | `404 Not Found`            | Returns descriptive error message.                                         |

---

## 7. Automated Testing

Run the full pytest suite from the repository root:

```bash
pytest backend/tests/ -v
```

The test suite covers:

- `test_health.py`: Health verification, unloaded model handling, model metadata.
- `test_prediction.py`:
  - District, Block, Panchayat listings and details
  - Input schema validation (landcover, date, missing fields)
  - Negative reference clipping
  - Service unavailable handling when model is missing
  - **Canonical Model Sanity Test**: Verifies predictions against `ml/results/test_predictions.csv` with zero floating point drift.
  - Historical time series queries and missing target handling
  - Empirical validation metrics
