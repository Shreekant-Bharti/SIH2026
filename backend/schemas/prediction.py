"""
Pydantic schemas for the FastAPI backend.
Defines schemas for predictions, health checks, metadata, and validation.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


ALLOWED_LANDCOVER_CODES = {4, 10, 12, 13}


class PredictionRequest(BaseModel):
    """
    Caller-side raw input payload for Panchayat rainfall prediction.
    GPCODE and DATE are administrative/temporal keys and are not direct model features.
    """
    gpcode: int = Field(..., description="Unique Local Government Directory Panchayat code")
    date: str = Field(..., description="Target date in YYYY-MM-DD format", json_schema_extra={"example": "2024-07-15"})
    temperature: float = Field(..., description="2m air temperature in Celsius")
    humidity: float = Field(..., description="Relative humidity percentage (0-100)")
    wind: float = Field(..., description="10m wind speed in m/s")
    et: float = Field(..., description="Potential / reference evapotranspiration in mm")
    elevation: float = Field(..., description="Terrain elevation in meters")
    slope: float = Field(..., description="Terrain slope in degrees")
    landcover: int = Field(..., description="Discrete land cover classification code (4, 10, 12, 13)")
    reference_rainfall: float = Field(..., description="Reference rainfall baseline in mm (clipped to >=0)")

    @field_validator("reference_rainfall")
    @classmethod
    def clip_reference_rainfall(cls, v: float) -> float:
        """
        Contract requirement: If reference rainfall is negative, clip to 0.0.
        """
        return max(0.0, float(v))

    def validate_rules(self) -> None:
        """
        Validates business rules that must return HTTP 400 Bad Request instead of 422.
        - Landcover must be in {4, 10, 12, 13}.
        - Date must be a valid calendar date in YYYY-MM-DD format.
        """
        if self.landcover not in ALLOWED_LANDCOVER_CODES:
            raise ValueError(
                f"Invalid landcover code: {self.landcover}. Allowed codes are {sorted(ALLOWED_LANDCOVER_CODES)}."
            )
        try:
            parsed_date = datetime.strptime(self.date, "%Y-%m-%d")
            # Enforce canonical representation (e.g. rejects 2024-02-30)
            if parsed_date.strftime("%Y-%m-%d") != self.date:
                raise ValueError
        except Exception:
            raise ValueError(f"Invalid date '{self.date}'. Expected valid calendar date in YYYY-MM-DD format.")


class PredictionResponse(BaseModel):
    """
    Response returned by POST /predict.
    Keeps internal residual hidden while exposing reconstructed rainfall.
    """
    gpcode: int
    date: str
    predicted_rainfall_mm: float
    reference_rainfall_mm: float
    model: str = "Ridge_Residual"
    model_version: str = "Ridge_Residual_v1"


class HealthResponse(BaseModel):
    """
    Response returned by GET /health.
    """
    status: str
    model_loaded: bool
    model: str = "Ridge_Residual"
    model_version: str = "Ridge_Residual_v1"


class ModelInfoResponse(BaseModel):
    """
    Response returned by GET /model/info.
    """
    model: str = "Ridge_Residual"
    version: str = "Ridge_Residual_v1"
    target: str = "Panchayat-level rainfall"
    prediction_type: str = "Residual downscaling"
    feature_count: int = 15
    status: str = "loaded"


class DistrictItem(BaseModel):
    name: str
    state: str


class DistrictsResponse(BaseModel):
    districts: List[DistrictItem]


class BlocksResponse(BaseModel):
    district: str
    blocks: List[str]


class PanchayatSummary(BaseModel):
    gpcode: int
    name: str


class PanchayatsResponse(BaseModel):
    block: str
    panchayats: List[PanchayatSummary]


class PanchayatDetail(BaseModel):
    gpcode: int
    name: str
    block: str
    district: str = "Dhanbad"
    elevation: float
    slope: float
    landcover: int


class HistoryItem(BaseModel):
    date: str
    observed_rainfall_mm: Optional[float] = None
    reference_rainfall_mm: float
    predicted_rainfall_mm: float


class HistoryResponse(BaseModel):
    gpcode: int
    data: List[HistoryItem]


class ValidationResponse(BaseModel):
    gpcode: int
    rmse: float
    mae: float
    bias: float
    correlation: float
    baseline_rmse: float
    model_rmse: float
