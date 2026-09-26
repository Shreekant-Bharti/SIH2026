"""
Data Service module for accessing administrative metadata, historical downscaling records,
and empirical validation metrics.
"""
from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("backend.services.data_service")

# Panchayats with missing observed IMD/gauge records
MISSING_OBSERVED_GPCODES = {111755, 111773}


class DataService:
    """
    Provides fast, in-memory lookup for Dhanbad districts, blocks, panchayats,
    historical time series data, and evaluation validation metrics.
    """
    def __init__(self, repo_root: Optional[Path] = None, model_service: Optional[Any] = None):
        self.repo_root = repo_root or REPO_ROOT
        self.model_service = model_service

        self.master_csv_path = self.repo_root / "ml" / "data" / "raw" / "master_dataset_v2.csv"
        self.test_preds_path = self.repo_root / "ml" / "results" / "test_predictions.csv"
        self.metrics_path = self.repo_root / "ml" / "results" / "panchayat_metrics.csv"

        self.panchayats_meta: Dict[int, Dict[str, Any]] = {}
        self.blocks: List[str] = []
        self.panchayats_by_block: Dict[str, List[Dict[str, Any]]] = {}
        self.validation_metrics: Dict[int, Dict[str, Any]] = {}
        self._test_preds_df: Optional[pd.DataFrame] = None
        self._missing_obs_df: Optional[pd.DataFrame] = None

        self._load_data()

    def _load_data(self) -> None:
        """Loads and pre-indexes administrative metadata and results."""
        logger.info("Initializing DataService from repository datasets...")

        # 1. Load static Panchayat metadata from master_dataset_v2.csv
        if self.master_csv_path.exists():
            df_master = pd.read_csv(self.master_csv_path)
            grouped = df_master.groupby("GPCODE").agg({
                "GPNAME": "first",
                "BLOCK": "first",
                "ELEVATION": "first",
                "SLOPE": "first",
                "LANDCOVER": "first"
            }).reset_index()

            for _, row in grouped.iterrows():
                gpcode = int(row["GPCODE"])
                self.panchayats_meta[gpcode] = {
                    "gpcode": gpcode,
                    "name": str(row["GPNAME"]),
                    "block": str(row["BLOCK"]),
                    "district": "Dhanbad",
                    "elevation": round(float(row["ELEVATION"]), 1),
                    "slope": round(float(row["SLOPE"]), 2),
                    "landcover": int(row["LANDCOVER"]),
                }

            self.blocks = sorted(list(set(p["block"] for p in self.panchayats_meta.values())))

            for block in self.blocks:
                self.panchayats_by_block[block.lower()] = [
                    {"gpcode": p["gpcode"], "name": p["name"]}
                    for p in sorted(
                        [p for p in self.panchayats_meta.values() if p["block"].lower() == block.lower()],
                        key=lambda x: x["name"]
                    )
                ]

            # Cache subset for Panchayats with missing observed rainfall (111755, 111773)
            missing_mask = df_master["GPCODE"].isin(MISSING_OBSERVED_GPCODES)
            self._missing_obs_df = df_master[missing_mask].copy()

            logger.info("Loaded metadata for %d panchayats across %d blocks.", len(self.panchayats_meta), len(self.blocks))
        else:
            logger.error("Master dataset not found at %s", self.master_csv_path)

        # 2. Load 2024 test predictions for historical queries
        if self.test_preds_path.exists():
            self._test_preds_df = pd.read_csv(self.test_preds_path)
            logger.info("Loaded test predictions with %d rows.", len(self._test_preds_df))
        else:
            logger.warning("Test predictions not found at %s", self.test_preds_path)

        # 3. Load empirical evaluation metrics
        if self.metrics_path.exists():
            df_metrics = pd.read_csv(self.metrics_path)
            for _, row in df_metrics.iterrows():
                gpcode = int(row["GPCODE"])
                self.validation_metrics[gpcode] = {
                    "gpcode": gpcode,
                    "rmse": round(float(row["ML_RMSE"]), 2),
                    "mae": round(float(row["ML_MAE"]), 2),
                    "bias": round(float(row["ML_Bias"]), 2),
                    "correlation": round(float(row["ML_Correlation"]), 2),
                    "baseline_rmse": round(float(row["REF_RMSE"]), 2),
                    "model_rmse": round(float(row["ML_RMSE"]), 2),
                }
            logger.info("Loaded validation metrics for %d panchayats.", len(self.validation_metrics))
        else:
            logger.warning("Panchayat metrics not found at %s", self.metrics_path)

    def get_districts(self) -> List[Dict[str, str]]:
        """Returns the list of covered districts."""
        return [{"name": "Dhanbad", "state": "Jharkhand"}]

    def get_blocks(self, district: str = "Dhanbad") -> Optional[List[str]]:
        """Returns the list of blocks for the specified district."""
        if district.strip().lower() != "dhanbad":
            return None
        return self.blocks

    def get_panchayats(self, block: str) -> Optional[List[Dict[str, Any]]]:
        """Returns the list of panchayats for the specified block."""
        return self.panchayats_by_block.get(block.strip().lower())

    def get_panchayat_by_gpcode(self, gpcode: int) -> Optional[Dict[str, Any]]:
        """Returns static terrain and administrative attributes for a GPCODE."""
        return self.panchayats_meta.get(gpcode)

    def get_validation_metrics(self, gpcode: int) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Returns validation metrics for a Panchayat.
        Returns:
            ("not_found", None) if GPCODE does not exist in dataset
            ("unavailable", None) if GPCODE has no observed ground-truth records (e.g. 111755, 111773)
            ("ok", metrics_dict) if valid metrics exist
        """
        if gpcode not in self.panchayats_meta:
            return "not_found", None

        if gpcode in MISSING_OBSERVED_GPCODES or gpcode not in self.validation_metrics:
            return "unavailable", None

        return "ok", self.validation_metrics[gpcode]

    def get_history(
        self,
        gpcode: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """
        Returns historical daily records (observed, reference, predicted) for a Panchayat.
        
        Returns:
            ("not_found", None) if GPCODE does not exist in dataset.
            ("ok", list_of_records) if found.
        """
        if gpcode not in self.panchayats_meta:
            return "not_found", None

        # Check if the panchayat is in test_predictions.csv
        if self._test_preds_df is not None and gpcode not in MISSING_OBSERVED_GPCODES:
            subset = self._test_preds_df[self._test_preds_df["GPCODE"] == gpcode]
            if start_date:
                subset = subset[subset["DATE"] >= start_date]
            if end_date:
                subset = subset[subset["DATE"] <= end_date]

            records: List[Dict[str, Any]] = []
            for _, row in subset.iterrows():
                obs_val = row["RAINFALL"]
                records.append({
                    "date": str(row["DATE"]),
                    "observed_rainfall_mm": round(float(obs_val), 2) if pd.notna(obs_val) else None,
                    "reference_rainfall_mm": round(float(row["REFERENCE_RAINFALL"]), 2),
                    "predicted_rainfall_mm": round(float(row["PREDICTED_RAINFALL"]), 2),
                })
            return "ok", records

        # For Panchayats with missing observed data (MAHESHPUR 2, RAJGANJ)
        if self._missing_obs_df is not None and gpcode in MISSING_OBSERVED_GPCODES:
            subset = self._missing_obs_df[self._missing_obs_df["GPCODE"] == gpcode]
            # If no date range specified, default to evaluation year 2024
            if not start_date and not end_date:
                subset = subset[(subset["DATE"] >= "2024-01-01") & (subset["DATE"] <= "2024-12-31")]
            else:
                if start_date:
                    subset = subset[subset["DATE"] >= start_date]
                if end_date:
                    subset = subset[subset["DATE"] <= end_date]

            records = []
            for _, row in subset.iterrows():
                ref_rain = float(row["REFERENCE_RAINFALL"])
                pred_rain = 0.0

                if self.model_service is not None and self.model_service.is_loaded:
                    try:
                        pred_rain, _ = self.model_service.predict(row.to_dict())
                    except Exception:
                        pred_rain = round(max(0.0, ref_rain), 2)
                else:
                    pred_rain = round(max(0.0, ref_rain), 2)

                records.append({
                    "date": str(row["DATE"]),
                    "observed_rainfall_mm": None,  # Strictly None, never fake!
                    "reference_rainfall_mm": round(ref_rain, 2),
                    "predicted_rainfall_mm": round(pred_rain, 2),
                })
            return "ok", records

        return "ok", []
