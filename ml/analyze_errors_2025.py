"""Read-only diagnostics for existing 2025 validation outputs.

Run from any directory with the project environment:
    python ml/analyze_errors_2025.py

Only predictions_2025.csv and panchayat_metrics_2025.csv are read. The script
creates two new error-analysis files and refuses to overwrite either one.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "ml" / "results" / "validation_2025"
PREDICTIONS_PATH = OUTPUT_DIR / "predictions_2025.csv"
PANCHAYAT_METRICS_PATH = OUTPUT_DIR / "panchayat_metrics_2025.csv"
JSON_PATH = OUTPUT_DIR / "error_analysis_2025.json"
CSV_PATH = OUTPUT_DIR / "error_analysis_2025.csv"

PREDICTION_COLUMNS = {
    "DATE",
    "GPCODE",
    "GPNAME",
    "BLOCK",
    "RAINFALL",
    "REFERENCE_RAINFALL",
    "REFERENCE_BASELINE_PREDICTION",
    "PREDICTED_RAINFALL",
    "EVALUATION_STATUS",
}
FEATURES_FOR_CORRELATION = [
    "REFERENCE_RAINFALL",
    "TEMPERATURE",
    "HUMIDITY",
    "WIND",
    "ET",
    "ELEVATION",
    "SLOPE",
]
EVENT_BINS = [
    ("0", lambda y: y == 0),
    (">0 to <2.5", lambda y: (y > 0) & (y < 2.5)),
    ("2.5 to <15", lambda y: (y >= 2.5) & (y < 15)),
    ("15 to <50", lambda y: (y >= 15) & (y < 50)),
    (">=50", lambda y: y >= 50),
]
CSV_COLUMNS = [
    "SECTION",
    "GROUP",
    "METRIC",
    "VALUE",
    "N",
    "NOTES",
    "DATE",
    "GPCODE",
    "GPNAME",
    "BLOCK",
    "RAINFALL",
    "REFERENCE_RAINFALL",
    "PREDICTED_RAINFALL",
    "ERROR",
]


def py_number(value: Any) -> float | int | str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, np.integer)):
        return int(value)
    return float(value)


def error_statistics(error: pd.Series) -> dict[str, float | int | None]:
    values = error.dropna().astype(float)
    if values.empty:
        return {key: None for key in ("mean", "median", "std", "min", "max", "p25", "p75", "p90", "p95", "p99")}
    return {
        "mean": float(values.mean()),
        "median": float(values.median()),
        "std": float(values.std()),
        "min": float(values.min()),
        "max": float(values.max()),
        "p25": float(values.quantile(0.25)),
        "p75": float(values.quantile(0.75)),
        "p90": float(values.quantile(0.90)),
        "p95": float(values.quantile(0.95)),
        "p99": float(values.quantile(0.99)),
    }


def regression_metrics(observed: pd.Series, predicted: pd.Series) -> dict[str, float | None]:
    paired = pd.concat([observed, predicted], axis=1).dropna()
    y = paired.iloc[:, 0].to_numpy(dtype=float)
    p = paired.iloc[:, 1].to_numpy(dtype=float)
    if len(y) == 0:
        return {key: None for key in ("MAE", "RMSE", "R2", "Bias", "Correlation")}

    error = p - y
    variance = float(np.sum((y - y.mean()) ** 2))
    r2 = None if variance <= 0 else float(1 - np.sum(error**2) / variance)
    correlation = (
        None
        if np.std(y) <= 1e-8 or np.std(p) <= 1e-8
        else float(np.corrcoef(y, p)[0, 1])
    )
    return {
        "MAE": float(np.mean(np.abs(error))),
        "RMSE": float(np.sqrt(np.mean(error**2))),
        "R2": r2,
        "Bias": float(np.mean(error)),
        "Correlation": correlation,
    }


def subset_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "n": int(len(frame)),
        "model": regression_metrics(frame["RAINFALL"], frame["PREDICTED_RAINFALL"]),
        "reference": regression_metrics(
            frame["RAINFALL"], frame["REFERENCE_BASELINE_PREDICTION"]
        ),
        "mean_observed": None if frame.empty else float(frame["RAINFALL"].mean()),
        "mean_predicted": None if frame.empty else float(frame["PREDICTED_RAINFALL"].mean()),
        "mean_reference": None
        if frame.empty
        else float(frame["REFERENCE_BASELINE_PREDICTION"].mean()),
        "mean_signed_error": None
        if frame.empty
        else float((frame["PREDICTED_RAINFALL"] - frame["RAINFALL"]).mean()),
        "mean_reference_minus_model_mae": None
        if frame.empty
        else float(
            regression_metrics(frame["RAINFALL"], frame["REFERENCE_BASELINE_PREDICTION"])["MAE"]
            - regression_metrics(frame["RAINFALL"], frame["PREDICTED_RAINFALL"])["MAE"]
        ),
        "mean_reference_minus_model_rmse": None
        if frame.empty
        else float(
            regression_metrics(frame["RAINFALL"], frame["REFERENCE_BASELINE_PREDICTION"])["RMSE"]
            - regression_metrics(frame["RAINFALL"], frame["PREDICTED_RAINFALL"])["RMSE"]
        ),
    }


def add_metric_rows(
    output_rows: list[dict[str, Any]],
    section: str,
    group: str,
    values: dict[str, Any],
    n: int | None = None,
    notes: str = "",
) -> None:
    def flatten(items: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        flat: dict[str, Any] = {}
        for key, value in items.items():
            name = f"{prefix}_{key}" if prefix else key
            if isinstance(value, dict):
                flat.update(flatten(value, name))
            else:
                flat[name] = value
        return flat

    for metric, value in flatten(values).items():
        output_rows.append(
            {
                "SECTION": section,
                "GROUP": group,
                "METRIC": metric,
                "VALUE": py_number(value),
                "N": n,
                "NOTES": notes,
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace only the two error-analysis outputs generated by this script.",
    )
    args = parser.parse_args()

    if not PREDICTIONS_PATH.is_file():
        raise FileNotFoundError(PREDICTIONS_PATH)
    if not PANCHAYAT_METRICS_PATH.is_file():
        raise FileNotFoundError(PANCHAYAT_METRICS_PATH)
    if (JSON_PATH.exists() or CSV_PATH.exists()) and not args.overwrite:
        raise FileExistsError(
            "Refusing to overwrite existing error-analysis outputs: "
            f"{JSON_PATH if JSON_PATH.exists() else CSV_PATH}"
        )

    predictions = pd.read_csv(PREDICTIONS_PATH)
    panchayat_metrics = pd.read_csv(PANCHAYAT_METRICS_PATH)
    missing_columns = sorted(PREDICTION_COLUMNS - set(predictions.columns))
    if missing_columns:
        raise ValueError(f"Prediction file lacks required columns: {missing_columns}")

    frame = predictions.loc[
        predictions["RAINFALL"].notna()
        & predictions["PREDICTED_RAINFALL"].notna()
        & predictions["REFERENCE_BASELINE_PREDICTION"].notna()
    ].copy()
    if frame.empty:
        raise ValueError("No fully evaluated rows found in predictions_2025.csv")

    frame["DATE"] = pd.to_datetime(frame["DATE"], format="%Y-%m-%d")
    frame["ERROR"] = frame["PREDICTED_RAINFALL"] - frame["RAINFALL"]
    frame["ABS_ERROR"] = frame["ERROR"].abs()
    frame["REFERENCE_ERROR"] = (
        frame["REFERENCE_BASELINE_PREDICTION"] - frame["RAINFALL"]
    )
    frame["ABS_ERROR_REFERENCE"] = frame["REFERENCE_ERROR"].abs()

    error = frame["ERROR"]
    n = len(frame)
    overall_model = regression_metrics(frame["RAINFALL"], frame["PREDICTED_RAINFALL"])
    overall_reference = regression_metrics(
        frame["RAINFALL"], frame["REFERENCE_BASELINE_PREDICTION"]
    )

    distribution = error_statistics(error)
    distribution.update(
        {
            "n": int(n),
            "underpredicted_pct": float((error < 0).mean() * 100),
            "overpredicted_pct": float((error > 0).mean() * 100),
            "exact_zero_error_count": int((error == 0).sum()),
            "exact_zero_error_pct": float((error == 0).mean() * 100),
        }
    )
    absolute_error_distribution = error_statistics(frame["ABS_ERROR"])
    absolute_error_distribution["n"] = int(n)

    dry = frame.loc[frame["RAINFALL"] == 0].copy()
    dry_metrics = subset_metrics(dry)
    dry_prediction = dry["PREDICTED_RAINFALL"]
    dry_metrics["model_mean_prediction"] = None if dry.empty else float(dry_prediction.mean())
    dry_metrics["model_median_prediction"] = None if dry.empty else float(dry_prediction.median())
    dry_metrics["model_mae"] = dry_metrics["model"]["MAE"]
    dry_metrics["model_rmse"] = dry_metrics["model"]["RMSE"]
    dry_metrics["reference_mae"] = dry_metrics["reference"]["MAE"]
    dry_metrics["reference_rmse"] = dry_metrics["reference"]["RMSE"]
    for label, mask in (
        ("predicted_lt_0_1_mm_pct", dry_prediction < 0.1),
        ("predicted_lt_1_mm_pct", dry_prediction < 1),
        ("predicted_ge_1_mm_pct", dry_prediction >= 1),
        ("predicted_ge_2_5_mm_pct", dry_prediction >= 2.5),
    ):
        dry_metrics[label] = None if dry.empty else float(mask.mean() * 100)

    event_rows: list[dict[str, Any]] = []
    mae_contributions: list[dict[str, Any]] = []
    for label, mask_fn in EVENT_BINS:
        subset = frame.loc[mask_fn(frame["RAINFALL"])].copy()
        summary = subset_metrics(subset)
        model_mae = summary["model"]["MAE"]
        reference_mae = summary["reference"]["MAE"]
        model_rmse = summary["model"]["RMSE"]
        reference_rmse = summary["reference"]["RMSE"]
        summary.update(
            {
                "bin": label,
                "model_minus_reference_mae": None
                if model_mae is None or reference_mae is None
                else model_mae - reference_mae,
                "model_minus_reference_rmse": None
                if model_rmse is None or reference_rmse is None
                else model_rmse - reference_rmse,
                "difference_in_absolute_error_sum": float(
                    subset["ABS_ERROR"].sum() - subset["ABS_ERROR_REFERENCE"].sum()
                ),
            }
        )
        event_rows.append(summary)
        mae_contributions.append(
            {
                "bin": label,
                "n": int(len(subset)),
                "difference_in_absolute_error_sum": summary[
                    "difference_in_absolute_error_sum"
                ],
                "contribution_to_overall_mae_gap_mm": summary[
                    "difference_in_absolute_error_sum"
                ]
                / n,
            }
        )

    extreme = frame.loc[frame["RAINFALL"] >= 50].copy()
    extreme_model_error = extreme["PREDICTED_RAINFALL"] - extreme["RAINFALL"]
    extreme_reference_error = (
        extreme["REFERENCE_BASELINE_PREDICTION"] - extreme["RAINFALL"]
    )
    extreme_summary = subset_metrics(extreme)
    extreme_summary.update(
        {
            "model_underprediction_pct": None
            if extreme.empty
            else float((extreme_model_error < 0).mean() * 100),
            "reference_underprediction_pct": None
            if extreme.empty
            else float((extreme_reference_error < 0).mean() * 100),
        }
    )
    top_events = (
        extreme.sort_values(
            ["RAINFALL", "DATE", "GPCODE"],
            ascending=[False, True, True],
            kind="stable",
        )
        .head(20)
    )
    top_event_records = [
        {
            "DATE": row.DATE.strftime("%Y-%m-%d"),
            "GPCODE": int(row.GPCODE),
            "GPNAME": str(row.GPNAME),
            "BLOCK": str(row.BLOCK),
            "RAINFALL": float(row.RAINFALL),
            "REFERENCE_RAINFALL": float(row.REFERENCE_RAINFALL),
            "PREDICTED_RAINFALL": float(row.PREDICTED_RAINFALL),
            "ERROR": float(row.ERROR),
        }
        for row in top_events.itertuples(index=False)
    ]

    monsoon = frame.loc[frame["DATE"].dt.month.isin([6, 7, 8, 9])].copy()
    monsoon_summary = subset_metrics(monsoon)
    monsoon_bins = []
    for label, mask_fn in EVENT_BINS:
        subset = monsoon.loc[mask_fn(monsoon["RAINFALL"])].copy()
        summary = subset_metrics(subset)
        monsoon_bins.append(
            {
                "bin": label,
                "n": summary["n"],
                "model_mae": summary["model"]["MAE"],
                "reference_mae": summary["reference"]["MAE"],
                "model_rmse": summary["model"]["RMSE"],
                "reference_rmse": summary["reference"]["RMSE"],
            }
        )

    monthly_rows = []
    for month in range(1, 13):
        subset = frame.loc[frame["DATE"].dt.month == month]
        model = regression_metrics(subset["RAINFALL"], subset["PREDICTED_RAINFALL"])
        reference = regression_metrics(
            subset["RAINFALL"], subset["REFERENCE_BASELINE_PREDICTION"]
        )
        monthly_rows.append(
            {
                "month": datetime(2025, month, 1).strftime("%B"),
                "n": int(len(subset)),
                "model_rmse": model["RMSE"],
                "reference_rmse": reference["RMSE"],
                "model_mae": model["MAE"],
                "reference_mae": reference["MAE"],
                "model_bias": model["Bias"],
                "reference_bias": reference["Bias"],
            }
        )

    block_rows = []
    for block, subset in frame.groupby("BLOCK", sort=True):
        summary = subset_metrics(subset)
        block_rows.append(
            {
                "block": str(block),
                "n": summary["n"],
                "model_rmse": summary["model"]["RMSE"],
                "reference_rmse": summary["reference"]["RMSE"],
                "model_minus_reference_rmse": summary["model"]["RMSE"]
                - summary["reference"]["RMSE"],
                "model_mae": summary["model"]["MAE"],
                "reference_mae": summary["reference"]["MAE"],
                "model_bias": summary["model"]["Bias"],
                "model_better_than_reference_rmse": summary["model"]["RMSE"]
                < summary["reference"]["RMSE"],
            }
        )

    gp_delta = panchayat_metrics["MODEL_RMSE"] - panchayat_metrics["REFERENCE_RMSE"]
    panchayat_summary = {
        "n_panchayats": int(len(panchayat_metrics)),
        "model_rmse_lower_count": int((gp_delta < 0).sum()),
        "model_rmse_higher_count": int((gp_delta > 0).sum()),
        "model_rmse_equal_count": int((gp_delta == 0).sum()),
        "model_minus_reference_rmse_distribution": {
            "p25": float(gp_delta.quantile(0.25)),
            "median": float(gp_delta.median()),
            "p75": float(gp_delta.quantile(0.75)),
            "min": float(gp_delta.min()),
            "max": float(gp_delta.max()),
        },
    }

    abs_error = frame["ABS_ERROR"]
    feature_correlations: dict[str, Any] = {}
    for feature in FEATURES_FOR_CORRELATION:
        if feature not in frame.columns:
            feature_correlations[feature] = {
                "correlation": None,
                "status": "unavailable",
                "reason": "Feature is not present in predictions_2025.csv; analysis is limited to the specified result files.",
            }
            continue
        paired = pd.concat([abs_error, pd.to_numeric(frame[feature], errors="coerce")], axis=1).dropna()
        feature_correlations[feature] = {
            "correlation": None
            if len(paired) < 2 or paired.iloc[:, 0].std() <= 1e-12 or paired.iloc[:, 1].std() <= 1e-12
            else float(paired.iloc[:, 0].corr(paired.iloc[:, 1])),
            "status": "computed",
            "n": int(len(paired)),
            "interpretation": "Correlation only; not causal.",
        }

    mae_gap = overall_model["MAE"] - overall_reference["MAE"]
    positive_contributions = [item for item in mae_contributions if item["difference_in_absolute_error_sum"] > 0]
    main_mae_driver = (
        max(positive_contributions, key=lambda item: item["difference_in_absolute_error_sum"])["bin"]
        if positive_contributions
        else None
    )
    main_mae_driver_label = (
        "0 mm (zero-rainfall days)" if main_mae_driver == "0" else main_mae_driver
    )

    report = {
        "analysis_label": "2025 historical out-of-time validation error analysis",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": [
            str(PREDICTIONS_PATH.relative_to(ROOT)),
            str(PANCHAYAT_METRICS_PATH.relative_to(ROOT)),
        ],
        "n_evaluated": int(n),
        "prediction_error_definition": "PREDICTED_RAINFALL - RAINFALL; negative means underprediction.",
        "reference_prediction_column": "REFERENCE_BASELINE_PREDICTION (production-clipped baseline)",
        "prediction_error_distribution": distribution,
        "absolute_error_distribution": absolute_error_distribution,
        "dry_day_observed_zero": dry_metrics,
        "observed_rainfall_bins": event_rows,
        "extreme_events_observed_ge_50_mm": {
            **extreme_summary,
            "top_20_events": top_event_records,
        },
        "monsoon_june_september": {
            **monsoon_summary,
            "rainfall_bins": monsoon_bins,
        },
        "monthly_performance": monthly_rows,
        "block_performance": {
            "metrics": block_rows,
            "model_rmse_lower_blocks": sorted(
                row["block"] for row in block_rows if row["model_better_than_reference_rmse"]
            ),
            "model_rmse_higher_blocks": sorted(
                row["block"] for row in block_rows if not row["model_better_than_reference_rmse"]
            ),
        },
        "panchayat_rmse_distribution": panchayat_summary,
        "absolute_error_feature_correlations": feature_correlations,
        "mae_gap_diagnostic": {
            "model_mae_minus_reference_mae": float(mae_gap),
            "bin_absolute_error_contributions": mae_contributions,
            "largest_positive_contributor_bin": main_mae_driver,
            "interpretation": (
                f"{main_mae_driver_label} contributes the largest positive difference in summed absolute error between model and reference."
                if main_mae_driver
                else "No rainfall bin has a positive model-minus-reference absolute-error contribution."
            ),
        },
    }

    output_rows: list[dict[str, Any]] = []
    add_metric_rows(output_rows, "prediction_error_distribution", "all", distribution, n)
    add_metric_rows(output_rows, "absolute_error_distribution", "all", absolute_error_distribution, n)
    add_metric_rows(output_rows, "dry_day_observed_zero", "0 mm", dry_metrics, len(dry))
    for row in event_rows:
        group = row["bin"]
        add_metric_rows(output_rows, "observed_rainfall_bin", group, row, row["n"])
    add_metric_rows(output_rows, "extreme_observed_ge_50", ">=50 mm", extreme_summary, len(extreme))
    add_metric_rows(output_rows, "monsoon_june_september", "all", monsoon_summary, len(monsoon))
    for row in monsoon_bins:
        add_metric_rows(output_rows, "monsoon_rainfall_bin", row["bin"], row, row["n"])
    for row in monthly_rows:
        add_metric_rows(output_rows, "monthly_performance", row["month"], row, row["n"])
    for row in block_rows:
        add_metric_rows(output_rows, "block_performance", row["block"], row, row["n"])
    add_metric_rows(
        output_rows,
        "panchayat_rmse_distribution",
        "all Panchayats",
        {
            **{key: value for key, value in panchayat_summary.items() if key != "model_minus_reference_rmse_distribution"},
            **panchayat_summary["model_minus_reference_rmse_distribution"],
        },
        panchayat_summary["n_panchayats"],
    )
    for feature, values in feature_correlations.items():
        add_metric_rows(
            output_rows,
            "absolute_error_feature_correlation",
            feature,
            {"correlation": values["correlation"]},
            values.get("n"),
            values.get("reason", values.get("interpretation", "")),
        )
    for index, row in enumerate(top_event_records, start=1):
        output_rows.append(
            {
                "SECTION": "top_20_extreme_events",
                "GROUP": f"rank_{index}",
                "METRIC": "observed_rainfall_event",
                "VALUE": row["RAINFALL"],
                "N": len(top_event_records),
                "NOTES": "Diagnostic event listing only; not a Panchayat ranking.",
                **row,
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with JSON_PATH.open("w" if args.overwrite else "x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, allow_nan=False)
    pd.DataFrame(output_rows, columns=CSV_COLUMNS).to_csv(CSV_PATH, index=False)

    print("MAIN FINDINGS:")
    print(
        f"1. Mean error {distribution['mean']:.4f} mm; underpredicted "
        f"{distribution['underpredicted_pct']:.2f}% and overpredicted "
        f"{distribution['overpredicted_pct']:.2f}%."
    )
    print(
        f"2. Dry-day model MAE/RMSE {dry_metrics['model_mae']:.4f}/"
        f"{dry_metrics['model_rmse']:.4f} mm vs reference "
        f"{dry_metrics['reference_mae']:.4f}/{dry_metrics['reference_rmse']:.4f} mm; "
        f"model predicts <0.1 mm on {dry_metrics['predicted_lt_0_1_mm_pct']:.2f}% of dry observations."
    )
    print(
        f"3. The largest positive contribution to the model's MAE gap comes from "
        f"the {main_mae_driver_label} observed-rainfall bin."
    )
    print(
        f"4. For >=50 mm events (n={len(extreme)}), model/reference underpredict "
        f"{extreme_summary['model_underprediction_pct']:.2f}%/"
        f"{extreme_summary['reference_underprediction_pct']:.2f}% of events."
    )
    print(
        f"5. Model RMSE is lower in {panchayat_summary['model_rmse_lower_count']} of "
        f"{panchayat_summary['n_panchayats']} GPs; correlation fields absent from the "
        "prediction CSV are reported as unavailable."
    )
    print(
        "\nMODEL WEAKNESS: "
        f"Overall MAE exceeds reference by {mae_gap:.4f} mm; "
        f"the largest positive absolute-error contribution is {main_mae_driver_label}."
    )
    print(
        "MODEL STRENGTH: "
        f"Overall RMSE is lower than reference by "
        f"{overall_reference['RMSE'] - overall_model['RMSE']:.4f} mm."
    )
    print(
        "POTENTIAL NEXT EXPERIMENT: Analyze a dry-day occurrence gate and an "
        "extreme-rainfall error strategy offline; do not change the production model "
        "without a separately approved experiment."
    )
    print(f"\nCreated: {JSON_PATH.relative_to(ROOT)}")
    print(f"Created: {CSV_PATH.relative_to(ROOT)}")
    print(
        "FEATURE CORRELATION LIMITATION: Only REFERENCE_RAINFALL exists in "
        "predictions_2025.csv; other requested feature correlations are unavailable "
        "under the specified input-only constraint."
    )


if __name__ == "__main__":
    main()