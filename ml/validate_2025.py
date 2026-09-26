"""Run a read-only 2025 historical out-of-time validation of the frozen model."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.model_service import ModelService
from ml.src.evaluate import compute_regression_metrics
from ml.src.features import FEATURE_COLUMNS

SOURCE_PATH = REPO_ROOT / "data" / "masterdataset_2025.csv"
MASTER_PATH = REPO_ROOT / "ml" / "data" / "raw" / "master_dataset_v2.csv"
METADATA_PATH = REPO_ROOT / "data" / "production" / "panchayat_master_metadata.csv"
MODEL_PATH = REPO_ROOT / "models" / "Ridge_residual.joblib"
OUTPUT_DIR = REPO_ROOT / "ml" / "results" / "validation_2025"

REQUIRED_COLUMNS = [
    "DATE",
    "GPCODE",
    "GPNAME",
    "BLOCK",
    "RAINFALL",
    "REFERENCE_RAINFALL",
    "TEMPERATURE",
    "HUMIDITY",
    "WIND",
    "ET",
    "ELEVATION",
    "SLOPE",
    "LANDCOVER",
]
MODEL_INPUT_FIELDS = [
    "GPCODE",
    "DATE",
    "TEMPERATURE",
    "HUMIDITY",
    "WIND",
    "ET",
    "ELEVATION",
    "SLOPE",
    "LANDCOVER",
    "REFERENCE_RAINFALL",
]
TARGET_COLUMN = "RAINFALL"
OUTPUT_FILES = [
    "predictions_2025.csv",
    "overall_metrics_2025.csv",
    "overall_metrics_2025.json",
    "panchayat_metrics_2025.csv",
    "block_metrics_2025.csv",
    "seasonal_metrics_2025.csv",
    "event_bin_metrics_2025.csv",
]


def assert_source_integrity(source: pd.DataFrame) -> dict[str, Any]:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in source.columns]
    if missing_columns:
        raise ValueError(f"2025 CSV is missing required columns: {missing_columns}")

    if TARGET_COLUMN in FEATURE_COLUMNS:
        raise RuntimeError("Leakage check failed: RAINFALL is in FEATURE_COLUMNS")
    if TARGET_COLUMN in MODEL_INPUT_FIELDS:
        raise RuntimeError("Leakage check failed: RAINFALL is in model input fields")

    dates = pd.to_datetime(source["DATE"], format="%Y-%m-%d", errors="coerce")
    if dates.isna().any():
        raise ValueError(f"Found {int(dates.isna().sum())} invalid DATE values")
    if source.duplicated(["GPCODE", "DATE"]).any():
        raise ValueError("Duplicate GPCODE + DATE rows found; refusing ambiguous validation")

    metadata = pd.read_csv(METADATA_PATH, usecols=["GPCODE", "GPNAME", "BLOCK"])
    source_geo = source[["GPCODE", "GPNAME", "BLOCK"]].drop_duplicates()
    metadata_geo = metadata.drop_duplicates()
    source_codes = set(source_geo["GPCODE"].astype(int))
    metadata_codes = set(metadata_geo["GPCODE"].astype(int))
    if source_codes != metadata_codes:
        raise ValueError(
            "2025 GPCODE set does not match production metadata: "
            f"new-only={sorted(source_codes - metadata_codes)}, "
            f"missing={sorted(metadata_codes - source_codes)}"
        )

    expected_pairs = len(metadata_codes) * 365
    unique_pairs = source[["GPCODE", "DATE"]].drop_duplicates().shape[0]
    if len(source) != expected_pairs or unique_pairs != expected_pairs:
        raise ValueError(
            f"Expected {expected_pairs} unique daily GP rows; found "
            f"{len(source)} rows and {unique_pairs} unique pairs"
        )

    source_names = source_geo.set_index("GPCODE")["GPNAME"].astype(str)
    source_blocks = source_geo.set_index("GPCODE")["BLOCK"].astype(str)
    meta_names = metadata_geo.set_index("GPCODE")["GPNAME"].astype(str)
    meta_blocks = metadata_geo.set_index("GPCODE")["BLOCK"].astype(str)
    name_mismatch = source_names.sort_index().ne(meta_names.sort_index())
    block_mismatch = source_blocks.sort_index().ne(meta_blocks.sort_index())
    if name_mismatch.any() or block_mismatch.any():
        raise ValueError(
            "2025 geography mismatch against production metadata: "
            f"names={int(name_mismatch.sum())}, blocks={int(block_mismatch.sum())}"
        )

    return {
        "total_rows": int(len(source)),
        "panchayats": int(len(source_codes)),
        "blocks": int(source["BLOCK"].nunique()),
        "date_min": dates.min().strftime("%Y-%m-%d"),
        "date_max": dates.max().strftime("%Y-%m-%d"),
        "unique_dates": int(dates.nunique()),
        "duplicate_gp_date_pairs": 0,
        "feature_columns": FEATURE_COLUMNS,
        "leakage_check": {
            "target": TARGET_COLUMN,
            "target_in_feature_columns": False,
            "target_in_model_input_payload": False,
            "result": "PASS",
        },
    }


def get_model_input(row: Any) -> dict[str, Any]:
    """Build only the production raw-input contract; never include RAINFALL."""
    model_input = {
        "GPCODE": int(row.GPCODE),
        "DATE": str(row.DATE),
        "TEMPERATURE": float(row.TEMPERATURE),
        "HUMIDITY": float(row.HUMIDITY),
        "WIND": float(row.WIND),
        "ET": float(row.ET),
        "ELEVATION": float(row.ELEVATION),
        "SLOPE": float(row.SLOPE),
        "LANDCOVER": int(row.LANDCOVER),
        "REFERENCE_RAINFALL": float(row.REFERENCE_RAINFALL),
    }
    if TARGET_COLUMN in model_input:
        raise RuntimeError("Leakage check failed: RAINFALL entered model input")
    return model_input


def clipped_reference_baseline(value: float) -> float:
    """Match ModelService's existing max(reference_rainfall, 0) convention."""
    return max(0.0, float(value))


def metric_set(observed: pd.Series, prediction: pd.Series) -> dict[str, float]:
    values = compute_regression_metrics(
        observed.to_numpy(dtype=float), prediction.to_numpy(dtype=float)
    )
    return {
        "RMSE": values["RMSE"],
        "MAE": values["MAE"],
        "R2": values["R2"],
        "Bias": values["Bias"],
        "Correlation": values["Correlation"],
    }


def compare_predictions(frame: pd.DataFrame) -> dict[str, Any]:
    observed = frame["RAINFALL"]
    model_metrics = metric_set(observed, frame["PREDICTED_RAINFALL"])
    reference_metrics = metric_set(observed, frame["REFERENCE_BASELINE_PREDICTION"])
    rmse_improvement = reference_metrics["RMSE"] - model_metrics["RMSE"]
    mae_improvement = reference_metrics["MAE"] - model_metrics["MAE"]
    return {
        "n_observations": int(len(frame)),
        "model": model_metrics,
        "reference_baseline": reference_metrics,
        "improvement": {
            "rmse": rmse_improvement,
            "rmse_percent": rmse_improvement / reference_metrics["RMSE"] * 100.0,
            "mae": mae_improvement,
            "mae_percent": mae_improvement / reference_metrics["MAE"] * 100.0,
            "model_better_than_reference_rmse": bool(
                model_metrics["RMSE"] < reference_metrics["RMSE"]
            ),
        },
    }


def grouped_metrics(
    evaluated: pd.DataFrame, group_column: str, include_block: bool = False
) -> pd.DataFrame:
    records = []
    group_keys = [group_column]
    if group_column == "GPCODE":
        group_keys += ["GPNAME", "BLOCK"]
    elif include_block:
        group_keys += ["BLOCK"]

    for key, group in evaluated.groupby(group_keys, sort=True, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        labels = dict(zip(group_keys, key))
        comparison = compare_predictions(group)
        row = {
            "N_OBSERVATIONS": comparison["n_observations"],
            "MODEL_RMSE": comparison["model"]["RMSE"],
            "REFERENCE_RMSE": comparison["reference_baseline"]["RMSE"],
            "MODEL_MAE": comparison["model"]["MAE"],
            "REFERENCE_MAE": comparison["reference_baseline"]["MAE"],
            "MODEL_BIAS": comparison["model"]["Bias"],
            "REFERENCE_BIAS": comparison["reference_baseline"]["Bias"],
            "MODEL_R2": comparison["model"]["R2"],
            "REFERENCE_R2": comparison["reference_baseline"]["R2"],
            "MODEL_BETTER_THAN_REFERENCE_RMSE": comparison["improvement"][
                "model_better_than_reference_rmse"
            ],
        }
        row.update(labels)
        records.append(row)

    columns = group_keys + [
        "N_OBSERVATIONS",
        "MODEL_RMSE",
        "REFERENCE_RMSE",
        "MODEL_MAE",
        "REFERENCE_MAE",
        "MODEL_BIAS",
        "REFERENCE_BIAS",
        "MODEL_R2",
        "REFERENCE_R2",
        "MODEL_BETTER_THAN_REFERENCE_RMSE",
    ]
    return pd.DataFrame.from_records(records, columns=columns)


def event_metrics(evaluated: pd.DataFrame) -> pd.DataFrame:
    observed = evaluated["RAINFALL"]
    bins = [
        ("0 mm", observed == 0),
        (">0 to <2.5 mm", (observed > 0) & (observed < 2.5)),
        ("2.5 to <15 mm", (observed >= 2.5) & (observed < 15)),
        ("15 to <50 mm", (observed >= 15) & (observed < 50)),
        (">=50 mm", observed >= 50),
    ]
    rows = []
    for label, mask in bins:
        group = evaluated.loc[mask]
        if group.empty:
            rows.append(
                {
                    "RAINFALL_BIN": label,
                    "N_OBSERVATIONS": 0,
                    "MODEL_MAE": None,
                    "REFERENCE_MAE": None,
                    "MODEL_RMSE": None,
                    "REFERENCE_RMSE": None,
                }
            )
            continue
        comparison = compare_predictions(group)
        rows.append(
            {
                "RAINFALL_BIN": label,
                "N_OBSERVATIONS": comparison["n_observations"],
                "MODEL_MAE": comparison["model"]["MAE"],
                "REFERENCE_MAE": comparison["reference_baseline"]["MAE"],
                "MODEL_RMSE": comparison["model"]["RMSE"],
                "REFERENCE_RMSE": comparison["reference_baseline"]["RMSE"],
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"2025 validation dataset not found: {SOURCE_PATH}")
    if not MASTER_PATH.exists() or not METADATA_PATH.exists():
        raise FileNotFoundError("Existing master dataset or production metadata is missing")
    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise FileExistsError(
            f"Refusing to overwrite existing validation outputs in {OUTPUT_DIR}"
        )

    source = pd.read_csv(SOURCE_PATH)
    source_metadata = assert_source_integrity(source)

    if TARGET_COLUMN in FEATURE_COLUMNS:
        raise RuntimeError("Leakage check failed before prediction: RAINFALL is a feature")
    print(
        "LEAKAGE CHECK: PASS; RAINFALL is absent from FEATURE_COLUMNS and each "
        "ModelService.predict payload."
    )

    model_service = ModelService(model_path=MODEL_PATH)
    if not model_service.is_loaded:
        raise RuntimeError(f"Existing Ridge model did not load: {model_service.load_error}")

    evaluated_source = source.loc[source[TARGET_COLUMN].notna()].copy()
    if evaluated_source.empty:
        raise ValueError("No non-null 2025 RAINFALL targets are available")

    # Run one real row before the full validation; reuse its result in the output.
    sanity_row = next(evaluated_source.itertuples(index=False))
    sanity_prediction, _ = model_service.predict(get_model_input(sanity_row))
    sanity_key = (int(sanity_row.GPCODE), str(sanity_row.DATE))
    print("SANITY CHECK (canonical ModelService.predict):")
    print(f"  GPCODE: {sanity_key[0]}")
    print(f"  DATE: {sanity_key[1]}")
    print(f"  REFERENCE_RAINFALL: {float(sanity_row.REFERENCE_RAINFALL)}")
    print(f"  PREDICTED_RAINFALL: {sanity_prediction:.2f}")

    negative_reference = source.loc[source["REFERENCE_RAINFALL"] < 0]
    negative_details = {
        "count": int(len(negative_reference)),
        "minimum": None
        if negative_reference.empty
        else float(negative_reference["REFERENCE_RAINFALL"].min()),
        "dates": sorted(negative_reference["DATE"].astype(str).unique().tolist()),
        "affected_gpcodes": sorted(
            negative_reference["GPCODE"].astype(int).unique().tolist()
        ),
        "source_values_modified": False,
        "evaluation_convention": (
            "Source REFERENCE_RAINFALL values were not modified; inference/baseline "
            "evaluation follows the existing production convention."
        ),
    }

    prediction_rows = []
    for index, row in enumerate(source.itertuples(index=False), start=1):
        observed = row.RAINFALL
        output = {
            "DATE": str(row.DATE),
            "GPCODE": int(row.GPCODE),
            "GPNAME": str(row.GPNAME),
            "BLOCK": str(row.BLOCK),
            "RAINFALL": None if pd.isna(observed) else float(observed),
            "REFERENCE_RAINFALL": float(row.REFERENCE_RAINFALL),
            "REFERENCE_BASELINE_PREDICTION": None,
            "PREDICTED_RAINFALL": None,
            "PREDICTION_RESIDUAL": None,
            "ABS_ERROR_MODEL": None,
            "ABS_ERROR_REFERENCE": None,
            "EVALUATION_STATUS": "missing_observation",
        }
        if not pd.isna(observed):
            key = (int(row.GPCODE), str(row.DATE))
            if key == sanity_key:
                predicted = sanity_prediction
            else:
                predicted, _ = model_service.predict(get_model_input(row))
            reference_baseline = clipped_reference_baseline(row.REFERENCE_RAINFALL)
            model_error = predicted - float(observed)
            reference_error = reference_baseline - float(observed)
            output.update(
                {
                    "REFERENCE_BASELINE_PREDICTION": reference_baseline,
                    "PREDICTED_RAINFALL": predicted,
                    "PREDICTION_RESIDUAL": model_error,
                    "ABS_ERROR_MODEL": abs(model_error),
                    "ABS_ERROR_REFERENCE": abs(reference_error),
                    "EVALUATION_STATUS": "evaluated",
                }
            )
        prediction_rows.append(output)
        if index % 10000 == 0:
            print(f"Processed {index:,} of {len(source):,} source rows...")

    predictions = pd.DataFrame(prediction_rows)
    evaluated = predictions.loc[predictions["EVALUATION_STATUS"] == "evaluated"].copy()
    overall = compare_predictions(evaluated)

    # Seasonal comparisons are computed only from rows with observed RAINFALL.
    evaluated_dates = pd.to_datetime(evaluated["DATE"], format="%Y-%m-%d")
    monsoon_mask = evaluated_dates.dt.month.isin([6, 7, 8, 9])
    seasonal_rows = []
    for label, subset in (
        ("Monsoon (June-September)", evaluated.loc[monsoon_mask]),
        ("Non-monsoon (January-May, October-December)", evaluated.loc[~monsoon_mask]),
    ):
        comparison = compare_predictions(subset)
        seasonal_rows.append(
            {
                "PERIOD": label,
                "N_OBSERVATIONS": comparison["n_observations"],
                "MODEL_RMSE": comparison["model"]["RMSE"],
                "REFERENCE_RMSE": comparison["reference_baseline"]["RMSE"],
                "MODEL_MAE": comparison["model"]["MAE"],
                "REFERENCE_MAE": comparison["reference_baseline"]["MAE"],
                "MODEL_R2": comparison["model"]["R2"],
                "REFERENCE_R2": comparison["reference_baseline"]["R2"],
                "MODEL_BIAS": comparison["model"]["Bias"],
                "REFERENCE_BIAS": comparison["reference_baseline"]["Bias"],
                "MODEL_CORRELATION": comparison["model"]["Correlation"],
                "REFERENCE_CORRELATION": comparison["reference_baseline"]["Correlation"],
            }
        )

    panchayat_metrics = grouped_metrics(evaluated, "GPCODE")
    block_metrics = grouped_metrics(evaluated, "BLOCK")
    event_bin_metrics = event_metrics(evaluated)

    missing_observation_rows = source.loc[source[TARGET_COLUMN].isna()]
    missing_observation_gps = (
        missing_observation_rows[["GPCODE", "GPNAME"]]
        .drop_duplicates()
        .sort_values("GPCODE")
        .to_dict(orient="records")
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    metadata = {
        "validation_label": "2025 historical out-of-time validation",
        "source_csv": str(SOURCE_PATH.relative_to(REPO_ROOT)),
        "model_artifact": str(MODEL_PATH.relative_to(REPO_ROOT)),
        "model": model_service.MODEL_NAME,
        "model_version": model_service.MODEL_VERSION,
        "feature_engineering_module": "ml.src.features.extract_features",
        "feature_columns": FEATURE_COLUMNS,
        "raw_model_input_columns": MODEL_INPUT_FIELDS,
        "leakage_check": source_metadata["leakage_check"],
        "validation_period": {
            "start": source_metadata["date_min"],
            "end": source_metadata["date_max"],
        },
        "generated_at_utc": generated_at,
        "total_rows": source_metadata["total_rows"],
        "rows_evaluated": int(len(evaluated)),
        "rows_excluded_missing_rainfall": int(len(missing_observation_rows)),
        "missing_observation_rows": int(len(missing_observation_rows)),
        "missing_observation_gps": missing_observation_gps,
        "panchayats": source_metadata["panchayats"],
        "blocks": source_metadata["blocks"],
        "unique_dates": source_metadata["unique_dates"],
        "duplicate_gp_date_pairs": source_metadata["duplicate_gp_date_pairs"],
        "negative_reference_rainfall": negative_details,
        "source_provenance": "Source provenance cannot be established from the CSV alone.",
        "overall_metrics": overall,
        "seasonal_metrics": seasonal_rows,
        "event_bin_metrics": event_bin_metrics.to_dict(orient="records"),
        "reference_baseline_convention": (
            "Reference baseline uses max(REFERENCE_RAINFALL, 0), matching the "
            "production ModelService convention. Original source values are retained."
        ),
    }

    overall_csv = {
        "validation_label": metadata["validation_label"],
        "total_rows": metadata["total_rows"],
        "rows_evaluated": metadata["rows_evaluated"],
        "rows_excluded_missing_rainfall": metadata["rows_excluded_missing_rainfall"],
        "panchayats": metadata["panchayats"],
        "blocks": metadata["blocks"],
        "date_min": source_metadata["date_min"],
        "date_max": source_metadata["date_max"],
        "model_rmse": overall["model"]["RMSE"],
        "model_mae": overall["model"]["MAE"],
        "model_r2": overall["model"]["R2"],
        "model_bias": overall["model"]["Bias"],
        "model_correlation": overall["model"]["Correlation"],
        "reference_rmse": overall["reference_baseline"]["RMSE"],
        "reference_mae": overall["reference_baseline"]["MAE"],
        "reference_r2": overall["reference_baseline"]["R2"],
        "reference_bias": overall["reference_baseline"]["Bias"],
        "reference_correlation": overall["reference_baseline"]["Correlation"],
        "rmse_improvement": overall["improvement"]["rmse"],
        "rmse_improvement_percent": overall["improvement"]["rmse_percent"],
        "mae_improvement": overall["improvement"]["mae"],
        "mae_improvement_percent": overall["improvement"]["mae_percent"],
        "model_better_than_reference_rmse": overall["improvement"][
            "model_better_than_reference_rmse"
        ],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(OUTPUT_DIR / "predictions_2025.csv", index=False)
    pd.DataFrame([overall_csv]).to_csv(
        OUTPUT_DIR / "overall_metrics_2025.csv", index=False
    )
    with (OUTPUT_DIR / "overall_metrics_2025.json").open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2, allow_nan=False)
    panchayat_metrics.to_csv(OUTPUT_DIR / "panchayat_metrics_2025.csv", index=False)
    block_metrics.to_csv(OUTPUT_DIR / "block_metrics_2025.csv", index=False)
    pd.DataFrame(seasonal_rows).to_csv(
        OUTPUT_DIR / "seasonal_metrics_2025.csv", index=False
    )
    event_bin_metrics.to_csv(OUTPUT_DIR / "event_bin_metrics_2025.csv", index=False)

    print("\n2025 VALIDATION")
    print("----------------")
    print(f"Total rows: {metadata['total_rows']:,}")
    print(f"Rows evaluated: {metadata['rows_evaluated']:,}")
    print(f"Rows excluded: {metadata['rows_excluded_missing_rainfall']:,}")
    print(f"Panchayats: {metadata['panchayats']}")
    print(f"Blocks: {metadata['blocks']}")
    print(f"Date range: {source_metadata['date_min']} to {source_metadata['date_max']}")
    print("\nMODEL")
    for key, label in [("RMSE", "RMSE"), ("MAE", "MAE"), ("R2", "R²"), ("Bias", "Bias"), ("Correlation", "Correlation")]:
        print(f"{label}: {overall['model'][key]:.6f}")
    print("\nREFERENCE BASELINE")
    for key, label in [("RMSE", "RMSE"), ("MAE", "MAE"), ("R2", "R²"), ("Bias", "Bias"), ("Correlation", "Correlation")]:
        print(f"{label}: {overall['reference_baseline'][key]:.6f}")
    print("\nIMPROVEMENT")
    print(f"RMSE improvement: {overall['improvement']['rmse']:.6f}")
    print(f"RMSE improvement %: {overall['improvement']['rmse_percent']:.6f}")
    print(f"MAE improvement: {overall['improvement']['mae']:.6f}")
    print(f"MAE improvement %: {overall['improvement']['mae_percent']:.6f}")
    print("\nMONSOON")
    print(f"MODEL RMSE: {seasonal_rows[0]['MODEL_RMSE']:.6f}")
    print(f"REFERENCE RMSE: {seasonal_rows[0]['REFERENCE_RMSE']:.6f}")
    print("\nEVENT PERFORMANCE")
    print(event_bin_metrics.to_string(index=False))
    print(
        "\nMODEL_BETTER_THAN_REFERENCE_RMSE = "
        f"{'yes' if overall['improvement']['model_better_than_reference_rmse'] else 'no'}"
    )
    print(f"\nMISSING_OBSERVATION_ROWS = {len(missing_observation_rows)}")
    print(f"MISSING_OBSERVATION_GPS = {len(missing_observation_gps)}")
    print(f"NEGATIVE_REFERENCE_VALUES = {negative_details['count']}")
    print(f"NEGATIVE_REFERENCE_MIN = {negative_details['minimum']}")
    print(f"NEGATIVE_REFERENCE_DATES = {negative_details['dates']}")
    print(negative_details["evaluation_convention"])
    print(f"\nOutputs written to: {OUTPUT_DIR.relative_to(REPO_ROOT)}")
    print("Source provenance cannot be established from the CSV alone.")


if __name__ == "__main__":
    main()