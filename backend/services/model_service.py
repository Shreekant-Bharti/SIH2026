"""
Model Service module for serving the trained Ridge Residual model.
Loads the sklearn Pipeline from models/Ridge_residual.joblib and strictly reuses
ml/src/features.py for feature extraction to prevent train/serve skew.
"""
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Tuple, Union
import warnings

import joblib
import numpy as np
import pandas as pd

# Ensure repository root is on sys.path so ml.src.features can be imported
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.src.features import FEATURE_COLUMNS, extract_features

logger = logging.getLogger("backend.services.model_service")


class ModelService:
    """
    Manages loading and inference for the trained Ridge Residual model pipeline.
    """
    MODEL_NAME = "Ridge_Residual"
    MODEL_VERSION = "Ridge_Residual_v1"
    TARGET = "Panchayat-level rainfall"
    PREDICTION_TYPE = "Residual downscaling"
    FEATURE_COUNT = 15

    def __init__(self, model_path: Optional[Union[str, Path]] = None):
        if model_path is None:
            self.model_path = REPO_ROOT / "models" / "Ridge_residual.joblib"
        else:
            self.model_path = Path(model_path)

        self.model: Optional[Any] = None
        self._loaded: bool = False
        self.load_error: Optional[str] = None

        self._load_model()

    def _load_model(self) -> None:
        """
        Loads the pre-trained Ridge residual pipeline from disk.
        Fails safely if model is missing or corrupt.
        """
        if not self.model_path.exists():
            self._loaded = False
            self.load_error = f"Model file not found at {self.model_path}"
            logger.error(self.load_error)
            return

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                # Catch scikit-learn version mismatch warnings gracefully
                self.model = joblib.load(self.model_path)

            self._loaded = True
            self.load_error = None
            logger.info("Successfully loaded %s from %s", self.MODEL_VERSION, self.model_path)
        except Exception as e:
            self._loaded = False
            self.model = None
            self.load_error = f"Failed to load model: {str(e)}"
            logger.exception(self.load_error)

    @property
    def is_loaded(self) -> bool:
        """Returns True if the ML model pipeline is loaded and ready."""
        return self._loaded

    def get_info(self) -> Dict[str, Any]:
        """Returns model metadata for GET /model/info."""
        return {
            "model": self.MODEL_NAME,
            "version": self.MODEL_VERSION,
            "target": self.TARGET,
            "prediction_type": self.PREDICTION_TYPE,
            "feature_count": self.FEATURE_COUNT,
            "status": "loaded" if self._loaded else "not_loaded",
        }

    def predict(
        self,
        record: Union[Dict[str, Any], Any]
    ) -> Tuple[float, float]:
        """
        Runs residual inference and reconstructs localized rainfall.
        
        Args:
            record: Dictionary or Pydantic object containing:
                - date (YYYY-MM-DD)
                - temperature
                - humidity
                - wind
                - et
                - elevation
                - slope
                - landcover
                - reference_rainfall

        Returns:
            Tuple of (predicted_rainfall_mm, predicted_residual)
        """
        if not self._loaded or self.model is None:
            raise RuntimeError("Model is not loaded. Cannot serve predictions.")

        if hasattr(record, "model_dump"):
            raw_data = record.model_dump()
        elif hasattr(record, "dict"):
            raw_data = record.dict()
        else:
            raw_data = dict(record)

        # Normalize dictionary keys to uppercase for uniform access
        data = {str(k).upper(): v for k, v in raw_data.items()}

        reference_rainfall = max(0.0, float(data.get("REFERENCE_RAINFALL", 0.0)))

        # Build single-row DataFrame using canonical uppercase column names expected by ml.src.features
        row_dict = {
            "DATE": str(data["DATE"]),
            "TEMPERATURE": float(data["TEMPERATURE"]),
            "HUMIDITY": float(data["HUMIDITY"]),
            "WIND": float(data["WIND"]),
            "ET": float(data["ET"]),
            "ELEVATION": float(data["ELEVATION"]),
            "SLOPE": float(data["SLOPE"]),
            "LANDCOVER": int(data["LANDCOVER"]),
            "REFERENCE_RAINFALL": reference_rainfall,
        }

        df_raw = pd.DataFrame([row_dict])

        # Strictly reuse the canonical feature extraction module
        df_feat = extract_features(df_raw)

        # Select exactly the 15 feature columns
        X = df_feat[FEATURE_COLUMNS]

        # Predict residual using raw numpy array to avoid feature-name warnings on StandardScaler
        pred_res_array = self.model.predict(X.values)
        predicted_residual = float(pred_res_array[0])

        # Reconstruct localized rainfall: max(REFERENCE_RAINFALL + residual, 0)
        reconstructed_rainfall = max(0.0, reference_rainfall + predicted_residual)

        return round(reconstructed_rainfall, 2), round(predicted_residual, 4)
