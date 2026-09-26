"""
Comprehensive integration and unit test suite for prediction, administrative lookups,
canonical reproducibility, and error handling.
"""
from pathlib import Path
import sys
import pandas as pd
import pytest
from fastapi.testclient import TestClient

# Ensure repo root and backend dir are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent
for p in (str(REPO_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.main import app
import backend.main as main_module
from backend.services.model_service import ModelService


@pytest.fixture
def client():
    """Provides a TestClient instance with initialized services."""
    # Ensure fresh services are bound
    main_module.model_service = ModelService()
    return TestClient(app)


def test_districts(client):
    """
    Test 3: GET /districts returns covered districts (Dhanbad, Jharkhand).
    """
    response = client.get("/districts")
    assert response.status_code == 200
    data = response.json()
    assert "districts" in data
    assert any(d["name"] == "Dhanbad" and d["state"] == "Jharkhand" for d in data["districts"])


def test_blocks(client):
    """
    Test 4: GET /blocks?district=Dhanbad returns actual blocks from dataset.
    """
    response = client.get("/blocks?district=Dhanbad")
    assert response.status_code == 200
    data = response.json()
    assert data["district"] == "Dhanbad"
    assert "Baghmara" in data["blocks"]
    assert "Baliapur" in data["blocks"]
    assert "Dhanbad" in data["blocks"]
    assert "Govindpur" in data["blocks"]
    assert "Topchanchi" in data["blocks"]
    assert "Tundi" in data["blocks"]


def test_blocks_invalid_district(client):
    """
    Test: GET /blocks with non-covered district returns 404.
    """
    response = client.get("/blocks?district=Ranchi")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_panchayats(client):
    """
    Test 5: GET /panchayats?block=Baghmara returns actual Panchayats with GPCODE.
    """
    response = client.get("/panchayats?block=Baghmara")
    assert response.status_code == 200
    data = response.json()
    assert data["block"] == "Baghmara"
    panchayats = data["panchayats"]
    assert len(panchayats) > 0
    # Must contain MAHESHPUR 2 (111755) and RAJGANJ (111773)
    gpcodes = [p["gpcode"] for p in panchayats]
    assert 111755 in gpcodes
    assert 111773 in gpcodes


def test_panchayats_invalid_block(client):
    """
    Test: GET /panchayats with unknown block returns 404.
    """
    response = client.get("/panchayats?block=NonExistentBlock")
    assert response.status_code == 404


def test_panchayat_detail(client):
    """
    Test: GET /panchayat/{gpcode} returns static elevation, slope, and landcover.
    """
    response = client.get("/panchayat/111755")
    assert response.status_code == 200
    data = response.json()
    assert data["gpcode"] == 111755
    assert data["name"] == "MAHESHPUR 2"
    assert data["block"] == "Baghmara"
    assert data["district"] == "Dhanbad"
    assert isinstance(data["elevation"], float)
    assert isinstance(data["slope"], float)
    assert data["landcover"] in [4, 10, 12, 13]


def test_panchayat_detail_not_found(client):
    """
    Test: GET /panchayat/{gpcode} returns 404 for unknown GPCODE.
    """
    response = client.get("/panchayat/999999")
    assert response.status_code == 404


def test_prediction_input_matches_master_dataset(client):
    date = "2024-07-15"
    response = client.get(f"/input/111722?date={date}")
    assert response.status_code == 200
    data = response.json()

    master = pd.read_csv(
        REPO_ROOT / "ml" / "data" / "raw" / "master_dataset_v2.csv",
        usecols=[
            "DATE",
            "GPCODE",
            "RAINFALL",
            "REFERENCE_RAINFALL",
            "TEMPERATURE",
            "HUMIDITY",
            "WIND",
            "ET",
            "ELEVATION",
            "SLOPE",
            "LANDCOVER",
        ],
    )
    row = master[(master["GPCODE"] == 111722) & (master["DATE"] == date)].iloc[0]
    assert data["gpcode"] == int(row["GPCODE"])
    assert data["date"] == date
    for field in (
        "temperature",
        "humidity",
        "wind",
        "et",
        "elevation",
        "slope",
        "reference_rainfall",
    ):
        assert data[field] == pytest.approx(float(row[field.upper()]))
    assert data["landcover"] == int(row["LANDCOVER"])
    assert data["observed_rainfall_mm"] == pytest.approx(float(row["RAINFALL"]))


def test_prediction_input_rejects_unknown_gp_invalid_date_and_missing_date(client):
    assert client.get("/input/999999?date=2024-07-15").status_code == 404
    assert client.get("/input/111722?date=not-a-date").status_code == 400
    assert client.get("/input/111722?date=2025-01-01").status_code == 404


def test_prediction_input_keeps_missing_observation_null(client):
    response = client.get("/input/111755?date=2024-07-15")
    assert response.status_code == 200
    data = response.json()
    assert data["gpcode"] == 111755
    assert data["observed_rainfall_mm"] is None
    assert data["temperature"] is not None
    assert data["reference_rainfall"] is not None


def test_prediction_input_reports_incomplete_model_features(client, monkeypatch):
    data_service = main_module.get_data_service()
    incomplete = data_service._prediction_inputs.copy()
    incomplete.loc[(111722, "2024-07-15"), "TEMPERATURE"] = float("nan")
    monkeypatch.setattr(data_service, "_prediction_inputs", incomplete)

    response = client.get("/input/111722?date=2024-07-15")
    assert response.status_code == 422
    assert "TEMPERATURE" in response.json()["detail"]


def test_prediction_from_retrieved_input_runs_model(client):
    input_response = client.get("/input/111722?date=2024-07-15")
    assert input_response.status_code == 200
    prediction_response = client.post("/predict", json=input_response.json())
    assert prediction_response.status_code == 200
    prediction = prediction_response.json()
    assert prediction["gpcode"] == 111722
    assert prediction["date"] == "2024-07-15"
    assert prediction["predicted_rainfall_mm"] >= 0


def test_predict_valid_input(client):
    """
    Test 6: POST /predict with real valid input returns non-negative predicted rainfall.
    """
    payload = {
        "gpcode": 111755,
        "date": "2024-07-15",
        "temperature": 28.4,
        "humidity": 78.2,
        "wind": 2.7,
        "et": 4.1,
        "elevation": 215.4,
        "slope": 2.3,
        "landcover": 12,
        "reference_rainfall": 14.7,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["gpcode"] == 111755
    assert data["date"] == "2024-07-15"
    assert data["predicted_rainfall_mm"] >= 0.0
    assert data["reference_rainfall_mm"] == 14.7
    assert data["model"] == "Ridge_Residual"
    assert data["model_version"] == "Ridge_Residual_v1"


def test_predict_invalid_landcover(client):
    """
    Test 7: POST /predict with invalid LANDCOVER (e.g. 99) returns HTTP 400 Bad Request.
    """
    payload = {
        "gpcode": 111755,
        "date": "2024-07-15",
        "temperature": 28.4,
        "humidity": 78.2,
        "wind": 2.7,
        "et": 4.1,
        "elevation": 215.4,
        "slope": 2.3,
        "landcover": 99,
        "reference_rainfall": 14.7,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 400
    assert "landcover" in response.json()["detail"].lower()


def test_predict_invalid_date(client):
    """
    Test: POST /predict with invalid date format (e.g. 'abc') returns HTTP 400 Bad Request.
    """
    payload = {
        "gpcode": 111755,
        "date": "abc",
        "temperature": 28.4,
        "humidity": 78.2,
        "wind": 2.7,
        "et": 4.1,
        "elevation": 215.4,
        "slope": 2.3,
        "landcover": 12,
        "reference_rainfall": 14.7,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 400
    assert "date" in response.json()["detail"].lower()


def test_predict_missing_inputs(client):
    """
    Test 8: POST /predict with missing required fields returns HTTP 422 Unprocessable Entity.
    """
    payload = {
        "gpcode": 111755,
        "date": "2024-07-15",
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_negative_reference_rainfall(client):
    """
    Test 9: POST /predict with negative reference rainfall clips it to 0.0 per contract.
    """
    payload = {
        "gpcode": 111755,
        "date": "2024-07-15",
        "temperature": 28.4,
        "humidity": 78.2,
        "wind": 2.7,
        "et": 4.1,
        "elevation": 215.4,
        "slope": 2.3,
        "landcover": 12,
        "reference_rainfall": -12.5,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["reference_rainfall_mm"] == 0.0
    assert data["predicted_rainfall_mm"] >= 0.0


def test_predict_model_not_loaded(client, monkeypatch):
    """
    Test 10: If model is not loaded, /predict returns HTTP 503 Service Unavailable.
    Never returns dummy/fake predictions.
    """
    unloaded_ms = ModelService(model_path=Path("non_existent_model_path.joblib"))
    monkeypatch.setattr(main_module, "model_service", unloaded_ms)

    payload = {
        "gpcode": 111755,
        "date": "2024-07-15",
        "temperature": 28.4,
        "humidity": 78.2,
        "wind": 2.7,
        "et": 4.1,
        "elevation": 215.4,
        "slope": 2.3,
        "landcover": 12,
        "reference_rainfall": 14.7,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 503
    assert "not loaded" in response.json()["detail"].lower()


def test_model_canonical_sanity_match(client):
    """
    Test 35: Canonical Model Sanity Test
    Loads a known row from test_predictions.csv and clean_dataset.csv, sends it to /predict,
    and validates that the backend prediction matches the canonical stored prediction.
    """
    clean_csv_path = REPO_ROOT / "ml" / "data" / "processed" / "clean_dataset.csv"
    test_preds_path = REPO_ROOT / "ml" / "results" / "test_predictions.csv"

    assert clean_csv_path.exists(), "clean_dataset.csv required for sanity test"
    assert test_preds_path.exists(), "test_predictions.csv required for sanity test"

    df_clean = pd.read_csv(clean_csv_path)
    # Pick a row from 2024 with substantial rainfall
    wet_rows = df_clean[(df_clean["DATE"] >= "2024-01-01") & (df_clean["RAINFALL"] > 5.0)]
    assert len(wet_rows) > 0, "No wet rows found for 2024 in clean_dataset"
    sample_row = wet_rows.iloc[0]

    df_test_preds = pd.read_csv(test_preds_path)
    canonical = df_test_preds[
        (df_test_preds["DATE"] == sample_row["DATE"]) &
        (df_test_preds["GPCODE"] == sample_row["GPCODE"])
    ].iloc[0]

    payload = {
        "gpcode": int(sample_row["GPCODE"]),
        "date": str(sample_row["DATE"]),
        "temperature": float(sample_row["TEMPERATURE"]),
        "humidity": float(sample_row["HUMIDITY"]),
        "wind": float(sample_row["WIND"]),
        "et": float(sample_row["ET"]),
        "elevation": float(sample_row["ELEVATION"]),
        "slope": float(sample_row["SLOPE"]),
        "landcover": int(sample_row["LANDCOVER"]),
        "reference_rainfall": float(sample_row["REFERENCE_RAINFALL"]),
    }

    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    res_data = response.json()

    api_prediction = res_data["predicted_rainfall_mm"]
    canonical_prediction = round(float(canonical["PREDICTED_RAINFALL"]), 2)

    # Must match within tiny rounding tolerance (<= 0.01 mm)
    diff = abs(api_prediction - canonical_prediction)
    assert diff <= 0.01, f"Mismatch in prediction: API={api_prediction} vs Canonical={canonical_prediction}"


def test_history_endpoint_standard_panchayat(client):
    """
    Test: GET /history/{gpcode} returns observed, reference, and predicted rainfall.
    """
    response = client.get("/history/111722?start_date=2024-07-01&end_date=2024-07-05")
    assert response.status_code == 200
    data = response.json()
    assert data["gpcode"] == 111722
    assert len(data["data"]) == 5
    for item in data["data"]:
        assert "date" in item
        assert "reference_rainfall_mm" in item
        assert "predicted_rainfall_mm" in item
        assert isinstance(item["observed_rainfall_mm"], (float, int))


def test_history_endpoint_missing_observed_panchayat(client):
    """
    Test: GET /history/{gpcode} for MAHESHPUR 2 (111755) returns None for observed_rainfall_mm.
    Strictly forbids fake observed data.
    """
    response = client.get("/history/111755?start_date=2024-07-01&end_date=2024-07-05")
    assert response.status_code == 200
    data = response.json()
    assert data["gpcode"] == 111755
    assert len(data["data"]) == 5
    for item in data["data"]:
        assert item["observed_rainfall_mm"] is None
        assert item["reference_rainfall_mm"] is not None
        assert item["predicted_rainfall_mm"] is not None


def test_history_invalid_date_range(client):
    """
    Test: GET /history/{gpcode} with start_date > end_date returns 400.
    """
    response = client.get("/history/111722?start_date=2024-07-10&end_date=2024-07-05")
    assert response.status_code == 400


def test_validation_endpoint_available(client):
    """
    Test: GET /validation/{gpcode} returns empirical metrics (RMSE, MAE, etc.).
    """
    response = client.get("/validation/111722")
    assert response.status_code == 200
    data = response.json()
    assert data["gpcode"] == 111722
    assert "rmse" in data
    assert "mae" in data
    assert "r2" in data
    assert "baseline_rmse" in data
    assert "baseline_mae" in data
    assert "model_rmse" in data


def test_validation_endpoint_unavailable(client):
    """
    Test: GET /validation/{gpcode} for MAHESHPUR 2 returns 404 because observed ground truth is missing.
    """
    response = client.get("/validation/111755")
    assert response.status_code == 404
    assert "unavailable" in response.json()["detail"].lower()
