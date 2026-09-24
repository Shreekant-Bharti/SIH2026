#!/usr/bin/env python3
"""
Production Data Pipeline for master_dataset_v2.csv (Dhanbad Panchayat Rainfall Downscaling)
-----------------------------------------------------------------------------------------
Generates:
  1. panchayat_master_metadata.csv / .json  -> clean static Panchayat metadata for backend
  2. data_validation_report.md              -> duplicate / missing / invalid value report
  3. sample_production_input.csv / .json    -> sample batch for Deepak's /predict API testing

IMPORTANT GUARANTEES
---------------------
- master_dataset_v2.csv is NEVER modified (opened read-only, never written back).
- No ML features / model logic touched.
- Missing or invalid static values are REPORTED ONLY, never guessed or auto-filled.

ASSUMED /predict INPUT SCHEMA  (⚠ confirm with Deepak before using in production!)
------------------------------------------------------------------------------
Per handover doc Sections 4 & 13, the model consumes reference rainfall + daily
met vars + static features (RAINFALL is the target, GPNAME/BLOCK are metadata
only — not model inputs):

    GPCODE, DATE, REFERENCE_RAINFALL, TEMPERATURE, HUMIDITY, WIND, ET,
    ELEVATION, SLOPE, LANDCOVER

If Deepak's real contract differs (different column names/order, extra
fields), only edit SAMPLE_INPUT_COLUMNS below — nothing else needs to change.

USAGE
-----
    python production_pipeline.py \
        --input master_dataset_v2.csv \
        --outdir ./production_outputs \
        --sample-panchayats 30 \
        --sample-dates 3

Requires: pandas, numpy   (pip install pandas numpy)
"""

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ALLOWED_LANDCOVER = {4, 10, 12, 13}
DISTRICT_NAME = "Dhanbad"

STATIC_COLS = ["GPNAME", "BLOCK", "ELEVATION", "SLOPE", "LANDCOVER"]
REQUIRED_COLS = [
    "DATE", "GPCODE", "GPNAME", "BLOCK", "RAINFALL", "REFERENCE_RAINFALL",
    "TEMPERATURE", "HUMIDITY", "WIND", "ET", "ELEVATION", "SLOPE", "LANDCOVER",
]

# ---- EDIT HERE if Deepak's real /predict schema differs ----
SAMPLE_INPUT_COLUMNS = [
    "GPCODE", "DATE", "REFERENCE_RAINFALL", "TEMPERATURE", "HUMIDITY",
    "WIND", "ET", "ELEVATION", "SLOPE", "LANDCOVER",
]
# --------------------------------------------------------------


def load_dataset(path):
    print(f"[1/6] Loading dataset: {path}")
    df = pd.read_csv(path, parse_dates=["DATE"])
    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        sys.exit(f"ERROR: input file is missing expected columns: {missing_cols}")
    print(f"       Loaded {len(df):,} rows, {df['GPCODE'].nunique():,} unique GPCODEs")
    return df


def mode_or_nan(series):
    """Most frequent non-null value in a series; NaN if series is all-null."""
    s = series.dropna()
    if s.empty:
        return np.nan
    return s.mode(dropna=True).iloc[0]


def build_metadata(df):
    print("[2/6] Building Panchayat static metadata (per unique GPCODE)...")
    records = []
    issues = {
        "duplicate_gpcode_with_multiple_names": [],
        "static_value_mismatch": [],   # any static col with >1 unique non-null value across dates
        "invalid_landcover": [],
        "missing_values": [],          # per GPCODE, fully-missing static cols
    }

    grouped = df.groupby("GPCODE", sort=True)

    for gpcode, g in grouped:
        row = {"GPCODE": gpcode, "DISTRICT": DISTRICT_NAME}
        col_missing = []
        col_mismatch = []

        for col in STATIC_COLS:
            uniq_nonnull = g[col].dropna().unique()
            if len(uniq_nonnull) == 0:
                row[col] = np.nan
                col_missing.append(col)
            elif len(uniq_nonnull) > 1:
                # Per team decision: mismatched static values are NOT auto-resolved
                # to the majority value. Left blank in metadata and routed to
                # manual review instead of guessing which value is correct.
                col_mismatch.append(col)
                row[col] = np.nan
            else:
                row[col] = uniq_nonnull[0]

        if "GPNAME" in col_mismatch:
            issues["duplicate_gpcode_with_multiple_names"].append({
                "GPCODE": gpcode,
                "names_found": sorted(g["GPNAME"].dropna().unique().tolist()),
            })

        if col_mismatch:
            issues["static_value_mismatch"].append({
                "GPCODE": gpcode,
                "mismatched_columns": col_mismatch,
            })

        if col_missing:
            issues["missing_values"].append({
                "GPCODE": gpcode,
                "missing_columns": col_missing,
            })

        lc = row.get("LANDCOVER")
        landcover_valid = None
        if not pd.isna(lc):
            try:
                lc_int = int(lc)
            except (ValueError, TypeError):
                lc_int = None
            landcover_valid = lc_int in ALLOWED_LANDCOVER
            if not landcover_valid:
                issues["invalid_landcover"].append({
                    "GPCODE": gpcode,
                    "landcover_value": lc,
                })

        row["LANDCOVER_VALID"] = landcover_valid
        row["HAS_STATIC_MISMATCH"] = bool(col_mismatch)
        row["MISMATCHED_FIELDS_NEEDS_MANUAL_REVIEW"] = ",".join(col_mismatch) if col_mismatch else ""
        row["MISSING_STATIC_FIELDS"] = ",".join(col_missing) if col_missing else ""

        records.append(row)

    meta_df = pd.DataFrame.from_records(records)

    dup_date_gpcode = int(df.duplicated(subset=["DATE", "GPCODE"]).sum())
    issues["duplicate_date_gpcode_rows"] = dup_date_gpcode

    print(f"       Metadata built for {len(meta_df):,} unique Panchayats")
    return meta_df, issues


def write_metadata(meta_df, outdir):
    print("[3/6] Writing Panchayat metadata CSV + JSON...")
    csv_path = os.path.join(outdir, "panchayat_master_metadata.csv")
    json_path = os.path.join(outdir, "panchayat_master_metadata.json")

    cols_order = [
        "GPCODE", "GPNAME", "BLOCK", "DISTRICT", "ELEVATION", "SLOPE",
        "LANDCOVER", "LANDCOVER_VALID", "HAS_STATIC_MISMATCH",
        "MISMATCHED_FIELDS_NEEDS_MANUAL_REVIEW", "MISSING_STATIC_FIELDS",
    ]
    meta_df = meta_df[cols_order].sort_values("GPCODE")
    meta_df.to_csv(csv_path, index=False)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json.loads(meta_df.to_json(orient="records")), f, indent=2, ensure_ascii=False)

    print(f"       -> {csv_path}")
    print(f"       -> {json_path}")
    return csv_path, json_path


def write_validation_report(df, meta_df, issues, outdir):
    print("[4/6] Writing data validation report...")
    path = os.path.join(outdir, "data_validation_report.md")

    total_panchayats = meta_df["GPCODE"].nunique()
    total_rows = len(df)
    dup_date_gpcode = issues["duplicate_date_gpcode_rows"]
    n_name_dupes = len(issues["duplicate_gpcode_with_multiple_names"])
    n_mismatch = len(issues["static_value_mismatch"])
    n_invalid_lc = len(issues["invalid_landcover"])
    n_missing = len(issues["missing_values"])
    n_valid_lc = int((meta_df["LANDCOVER_VALID"] == True).sum())
    n_lc_missing = int(meta_df["LANDCOVER"].isna().sum())

    lines = []
    lines.append("# Panchayat Static Data — Validation Report\n")
    lines.append(f"Source file row count: **{total_rows:,}**  ")
    lines.append(f"Unique GPCODEs found: **{total_panchayats:,}**  ")
    lines.append("Expected (per handover doc): **239**\n")

    lines.append("## 1. GPCODE Uniqueness / Duplicate Mapping\n")
    lines.append(f"- Duplicate `DATE + GPCODE` rows in raw file: **{dup_date_gpcode}**")
    lines.append(f"- GPCODEs mapped to more than one GPNAME (ambiguous identity): **{n_name_dupes}**")
    for item in issues["duplicate_gpcode_with_multiple_names"]:
        lines.append(f"  - GPCODE `{item['GPCODE']}` -> names: {item['names_found']}")
    lines.append("")

    lines.append("## 2. Static Feature Consistency (GPNAME / BLOCK / ELEVATION / SLOPE / LANDCOVER)\n")
    lines.append(f"- GPCODEs with date-wise mismatch in >=1 static column: **{n_mismatch}**")
    lines.append("  (NOT auto-resolved to a majority value — left blank in metadata and routed to")
    lines.append("  manual review. These GPCODEs are also excluded from the production sample file.)")
    for item in issues["static_value_mismatch"]:
        lines.append(f"  - GPCODE `{item['GPCODE']}` -> mismatched columns: {item['mismatched_columns']}")
    lines.append("")

    lines.append("## 3. LANDCOVER Contract Check — allowed values {4, 10, 12, 13}\n")
    lines.append(f"- Panchayats with a VALID landcover value: **{n_valid_lc}**")
    lines.append(f"- Panchayats with an INVALID (out-of-contract) landcover value: **{n_invalid_lc}**")
    lines.append(f"- Panchayats with LANDCOVER missing entirely: **{n_lc_missing}**")
    if issues["invalid_landcover"]:
        lines.append("\n  Invalid values found:")
        for item in issues["invalid_landcover"]:
            lines.append(f"  - GPCODE `{item['GPCODE']}` -> LANDCOVER = {item['landcover_value']}")
    lines.append("")

    n_manual_review = int((meta_df["HAS_STATIC_MISMATCH"] == True).sum())
    lines.append("## 3b. GPCODEs Requiring Manual Review\n")
    lines.append(f"- Total GPCODEs with unresolved static mismatch (blank in metadata, excluded from production sample): **{n_manual_review}**\n")

    lines.append("## 4. Missing Static Values (reported only — nothing auto-filled)\n")
    lines.append(f"- GPCODEs with one or more fully-missing static fields: **{n_missing}**")
    for item in issues["missing_values"]:
        lines.append(f"  - GPCODE `{item['GPCODE']}` -> missing: {item['missing_columns']}")
    lines.append("")

    lines.append("## 5. RAINFALL Target Completeness (cross-check vs handover doc)\n")
    n_missing_rainfall = int(df["RAINFALL"].isna().sum())
    panchayats_missing_rainfall = sorted(df.loc[df["RAINFALL"].isna(), "GPCODE"].unique().tolist())
    lines.append(f"- Rows with missing RAINFALL: **{n_missing_rainfall:,}**")
    lines.append(f"- Panchayats affected: {panchayats_missing_rainfall}")
    lines.append("- Excluded from ML train/val/test only; retained in master file (handover Sec. 6).")
    lines.append("")

    all_clean = (dup_date_gpcode == 0 and n_name_dupes == 0 and n_mismatch == 0
                 and n_invalid_lc == 0 and n_missing == 0)
    lines.append("## 6. Summary\n")
    lines.append(f"- **Overall static data status: {'CLEAN' if all_clean else 'ISSUES FOUND — see sections above'}**")
    lines.append("- No values were auto-filled or guessed. Flagged GPCODEs need manual source-data correction before backend use.")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"       -> {path}")
    return path


def build_sample_production_input(df, meta_df, outdir, n_panchayats, n_dates, seed=42):
    print("[5/6] Building sample production input for /predict testing...")
    rng = np.random.default_rng(seed)

    # Prefer Panchayats with clean, valid static data so the sample works
    # out-of-the-box for API testing.
    clean_gpcodes = meta_df.loc[
        (meta_df["LANDCOVER_VALID"] == True) & (~meta_df["HAS_STATIC_MISMATCH"]),
        "GPCODE",
    ].tolist()

    pool = clean_gpcodes if len(clean_gpcodes) >= n_panchayats else meta_df["GPCODE"].tolist()
    n_panchayats = min(n_panchayats, len(pool))
    chosen_gpcodes = sorted(rng.choice(pool, size=n_panchayats, replace=False).tolist())

    all_dates = sorted(df["DATE"].dropna().unique())
    n_dates = min(n_dates, len(all_dates))
    chosen_dates = sorted(rng.choice(all_dates, size=n_dates, replace=False).tolist())

    sample = df[df["GPCODE"].isin(chosen_gpcodes) & df["DATE"].isin(chosen_dates)].copy()
    sample = sample[SAMPLE_INPUT_COLUMNS].sort_values(["GPCODE", "DATE"]).reset_index(drop=True)
    sample["DATE"] = sample["DATE"].dt.strftime("%Y-%m-%d")

    csv_path = os.path.join(outdir, "sample_production_input.csv")
    json_path = os.path.join(outdir, "sample_production_input.json")
    sample.to_csv(csv_path, index=False)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json.loads(sample.to_json(orient="records")), f, indent=2, ensure_ascii=False)

    print(f"       Sample: {len(chosen_gpcodes)} Panchayats x {len(chosen_dates)} dates = {len(sample)} rows")
    print(f"       -> {csv_path}")
    print(f"       -> {json_path}")
    return csv_path, json_path


def main():
    parser = argparse.ArgumentParser(description="Dhanbad Panchayat production data pipeline")
    parser.add_argument("--input", required=True, help="Path to master_dataset_v2.csv")
    parser.add_argument("--outdir", default="./production_outputs", help="Output directory")
    parser.add_argument("--sample-panchayats", type=int, default=30,
                         help="Number of Panchayats in sample /predict input (20-50 recommended)")
    parser.add_argument("--sample-dates", type=int, default=3,
                         help="Number of dates in sample /predict input (2-3 recommended)")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    df = load_dataset(args.input)
    meta_df, issues = build_metadata(df)
    write_metadata(meta_df, args.outdir)
    write_validation_report(df, meta_df, issues, args.outdir)
    build_sample_production_input(df, meta_df, args.outdir, args.sample_panchayats, args.sample_dates)

    print("[6/6] Done. master_dataset_v2.csv was NOT modified. No ML features/model changed.")


if __name__ == "__main__":
    main()
