"""
FastAPI application for SIH2026 localized Panchayat rainfall intelligence.
Serves the frozen Ridge Residual model pipeline (StandardScaler -> Ridge)
and provides administrative geography, historical evaluations, and validation metrics.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from pathlib import Path
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

# Ensure both repo root and backend directory are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent

for p in (str(REPO_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from backend.schemas.prediction import (
        BlocksResponse,
        DistrictsResponse,
        HealthResponse,
        HistoryResponse,
        ModelInfoResponse,
        PanchayatDetail,
        PanchayatsResponse,
        PredictionInputResponse,
        PredictionRequest,
        PredictionResponse,
        ValidationResponse,
    )
    from backend.services.data_service import DataService
    from backend.services.model_service import ModelService
except ImportError:
    from schemas.prediction import (
        BlocksResponse,
        DistrictsResponse,
        HealthResponse,
        HistoryResponse,
        ModelInfoResponse,
        PanchayatDetail,
        PanchayatsResponse,
        PredictionInputResponse,
        PredictionRequest,
        PredictionResponse,
        ValidationResponse,
    )
    from services.data_service import DataService
    from services.model_service import ModelService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backend.main")

# Global service instances
model_service: Optional[ModelService] = None
data_service: Optional[DataService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for startup and shutdown resource initialization.
    """
    global model_service, data_service
    logger.info("Initializing ML Model and Data services...")
    model_service = ModelService()
    data_service = DataService(model_service=model_service)
    logger.info(
        "Services initialized. Model status: %s",
        "LOADED" if model_service.is_loaded else "FAILED_TO_LOAD",
    )
    yield
    logger.info("Shutting down backend services...")


app = FastAPI(
    title="SIH2026 Panchayat Rainfall Intelligence API",
    description=(
        "Production-grade serving API for the Ridge Residual ML downscaling pipeline. "
        "Transforms coarse meteorological and terrain inputs into localized Panchayat-level rainfall estimates."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local frontend development (e.g. React / Vite on localhost:5173 or other ports)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_model_service() -> ModelService:
    """Dependency helper to get or initialize ModelService."""
    global model_service
    if model_service is None:
        model_service = ModelService()
    return model_service


def get_data_service() -> DataService:
    """Dependency helper to get or initialize DataService."""
    global data_service, model_service
    if data_service is None:
        ms = get_model_service()
        data_service = DataService(model_service=ms)
    return data_service


# -----------------------------------------------------------------------------
# 1. Health and Model Metadata Endpoints
# -----------------------------------------------------------------------------

@app.get("/", tags=["System"])
def root():
    """
    Root endpoint providing API information and documentation link.
    """
    return {
        "message": "SIH2026 Panchayat Rainfall Intelligence API is active",
        "status": "ok",
        "documentation": "/docs",
        "health": "/health",
        "model_info": "/model/info",
        "districts": "/districts",
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """
    Health check endpoint reporting API status and model availability.
    Fails closed: reports 'error' status if the trained model artifact is missing or unloadable.
    """
    ms = get_model_service()
    if ms.is_loaded:
        return HealthResponse(
            status="ok",
            model_loaded=True,
            model=ms.MODEL_NAME,
            model_version=ms.MODEL_VERSION,
        )
    return HealthResponse(
        status="error",
        model_loaded=False,
        model=ms.MODEL_NAME,
        model_version=ms.MODEL_VERSION,
    )


@app.get("/model/info", response_model=ModelInfoResponse, tags=["Model"])
def model_info():
    """
    Returns architectural specifications and feature schema metadata of the deployed model.
    """
    ms = get_model_service()
    info = ms.get_info()
    return ModelInfoResponse(**info)


# -----------------------------------------------------------------------------
# 2. Administrative Geography Endpoints
# -----------------------------------------------------------------------------

@app.get("/districts", response_model=DistrictsResponse, tags=["Geography"])
def get_districts():
    """
    Returns available administrative districts covered by the trained model.
    """
    ds = get_data_service()
    return DistrictsResponse(districts=ds.get_districts())


@app.get("/blocks", response_model=BlocksResponse, tags=["Geography"])
def get_blocks(district: str = Query("Dhanbad", description="District name")):
    """
    Returns administrative blocks for the requested district.
    """
    ds = get_data_service()
    blocks = ds.get_blocks(district=district)
    if blocks is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District '{district}' not found. Current coverage is limited to Dhanbad, Jharkhand.",
        )
    return BlocksResponse(district=district, blocks=blocks)


@app.get("/panchayats", response_model=PanchayatsResponse, tags=["Geography"])
def get_panchayats(block: str = Query(..., description="Block name")):
    """
    Returns the list of Panchayats (GPCODE and name) for a specified block.
    """
    ds = get_data_service()
    panchayats = ds.get_panchayats(block=block)
    if panchayats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block '{block}' not found.",
        )
    return PanchayatsResponse(block=block, panchayats=panchayats)


@app.get("/panchayat/{gpcode}", response_model=PanchayatDetail, tags=["Geography"])
def get_panchayat_detail(gpcode: int):
    """
    Returns terrain features (elevation, slope, landcover) and administrative metadata for a Panchayat.
    """
    ds = get_data_service()
    detail = ds.get_panchayat_by_gpcode(gpcode=gpcode)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Panchayat with GPCODE {gpcode} not found.",
        )
    return PanchayatDetail(**detail)


# -----------------------------------------------------------------------------
# 3. Model Inference Endpoint
# -----------------------------------------------------------------------------

@app.get("/input/{gpcode}", response_model=PredictionInputResponse, tags=["Inference"])
def get_prediction_input(
    gpcode: int,
    date: str = Query(..., description="Available dataset date in YYYY-MM-DD format"),
):
    """Returns real weather, terrain, reference and optional observed values for inference."""
    try:
        parsed = datetime.strptime(date, "%Y-%m-%d")
        if parsed.strftime("%Y-%m-%d") != date:
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date '{date}'. Expected valid YYYY-MM-DD.",
        )

    result, inputs = get_data_service().get_prediction_input(gpcode=gpcode, date=date)
    if result == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Panchayat with GPCODE {gpcode} not found.",
        )
    if result == "date_not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No source data found for GPCODE {gpcode} on {date}.",
        )
    if result == "unavailable":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The master input dataset is unavailable.",
        )
    if result == "incomplete":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Model inputs are missing: {', '.join(inputs['missing_fields'])}.",
        )
    return PredictionInputResponse(**inputs)


@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
def predict_rainfall(request: PredictionRequest):
    """
    Main prediction endpoint.
    Takes raw Panchayat weather and terrain attributes, computes canonical features
    via ml/src/features.py, evaluates the Ridge Residual pipeline, and returns reconstructed rainfall.
    """
    ms = get_model_service()

    # Fail closed if model is not loaded
    if not ms.is_loaded:
        logger.error("Predict called but model is not loaded: %s", ms.load_error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded or unavailable. Predictions cannot be served.",
        )

    # Validate business rules (allowed landcover, date format) -> HTTP 400 Bad Request
    try:
        request.validate_rules()
    except ValueError as e:
        logger.warning("Prediction validation failed for GPCODE %d: %s", request.gpcode, str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    try:
        pred_rainfall, pred_residual = ms.predict(request)
        
        # Log prediction event (timestamp, gpcode, date, model_version, status)
        now_utc = datetime.now(timezone.utc).isoformat()
        logger.info(
            "PREDICT_SUCCESS: timestamp=%s, gpcode=%d, date=%s, model_version=%s, status=ok, predicted_rainfall=%.2f",
            now_utc,
            request.gpcode,
            request.date,
            ms.MODEL_VERSION,
            pred_rainfall,
        )

        return PredictionResponse(
            gpcode=request.gpcode,
            date=request.date,
            predicted_rainfall_mm=pred_rainfall,
            reference_rainfall_mm=round(request.reference_rainfall, 2),
            model=ms.MODEL_NAME,
            model_version=ms.MODEL_VERSION,
        )
    except Exception as e:
        now_utc = datetime.now(timezone.utc).isoformat()
        logger.exception(
            "PREDICT_ERROR: timestamp=%s, gpcode=%d, date=%s, status=error, error=%s",
            now_utc,
            request.gpcode,
            request.date,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 4. Historical Records and Validation Endpoints
# -----------------------------------------------------------------------------

@app.get("/history/{gpcode}", response_model=HistoryResponse, tags=["Historical"])
def get_panchayat_history(
    gpcode: int,
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
):
    """
    Returns historical daily observed, reference, and predicted rainfall values for a Panchayat.
    Panchayats with missing observed data (e.g. MAHESHPUR 2, RAJGANJ) return null for observed_rainfall_mm.
    """
    # Date validation
    for dt_str, dt_label in ((start_date, "start_date"), (end_date, "end_date")):
        if dt_str:
            try:
                parsed = datetime.strptime(dt_str, "%Y-%m-%d")
                if parsed.strftime("%Y-%m-%d") != dt_str:
                    raise ValueError
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid {dt_label} format '{dt_str}'. Expected valid YYYY-MM-DD.",
                )

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"start_date '{start_date}' cannot be after end_date '{end_date}'.",
        )

    ds = get_data_service()
    status_code, history_data = ds.get_history(
        gpcode=gpcode, start_date=start_date, end_date=end_date
    )

    if status_code == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Panchayat with GPCODE {gpcode} not found.",
        )

    return HistoryResponse(gpcode=gpcode, data=history_data or [])


@app.get("/validation/{gpcode}", response_model=ValidationResponse, tags=["Validation"])
def get_panchayat_validation(gpcode: int):
    """
    Returns empirical validation metrics (RMSE, MAE, Bias, Correlation, Baseline RMSE) for a Panchayat.
    Returns 404 if Panchayat does not exist or if ground-truth records are unavailable.
    """
    ds = get_data_service()
    status_code, metrics = ds.get_validation_metrics(gpcode=gpcode)

    if status_code == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Panchayat with GPCODE {gpcode} not found.",
        )

    if status_code == "unavailable":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation metrics unavailable for GPCODE {gpcode}: observed ground-truth rainfall records are unavailable.",
        )

    return ValidationResponse(**metrics)
