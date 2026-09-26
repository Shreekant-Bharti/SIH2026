"""
Schemas package for FastAPI backend.
Supports both absolute and package-relative imports.
"""
try:
    from backend.schemas.prediction import (
        PredictionRequest,
        PredictionResponse,
        HealthResponse,
        ModelInfoResponse,
        DistrictItem,
        DistrictsResponse,
        BlocksResponse,
        PanchayatSummary,
        PanchayatsResponse,
        PanchayatDetail,
        HistoryItem,
        HistoryResponse,
        ValidationResponse,
        ALLOWED_LANDCOVER_CODES,
    )
except ImportError:
    from schemas.prediction import (
        PredictionRequest,
        PredictionResponse,
        HealthResponse,
        ModelInfoResponse,
        DistrictItem,
        DistrictsResponse,
        BlocksResponse,
        PanchayatSummary,
        PanchayatsResponse,
        PanchayatDetail,
        HistoryItem,
        HistoryResponse,
        ValidationResponse,
        ALLOWED_LANDCOVER_CODES,
    )

__all__ = [
    "PredictionRequest",
    "PredictionResponse",
    "HealthResponse",
    "ModelInfoResponse",
    "DistrictItem",
    "DistrictsResponse",
    "BlocksResponse",
    "PanchayatSummary",
    "PanchayatsResponse",
    "PanchayatDetail",
    "HistoryItem",
    "HistoryResponse",
    "ValidationResponse",
    "ALLOWED_LANDCOVER_CODES",
]
