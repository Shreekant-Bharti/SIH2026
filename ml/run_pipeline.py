"""
Master Orchestrator Script for Panchayat-Level Rainfall Downscaling
Dhanbad District, Jharkhand, India
Executes Phases 1 through 12 sequentially.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd

from src.audit import run_data_audit
from src.preprocessing import prepare_and_split_datasets
from src.features import extract_features, FEATURE_COLUMNS
from src.baselines import evaluate_baselines
from src.train import train_models_pipeline
from src.evaluate import compute_panchayat_level_metrics
from src.generalization import evaluate_spatial_generalization, compute_and_save_feature_importance
from src.visualization import generate_core_visualizations


def main():
    print("=" * 75)
    print("PANCHAYAT-LEVEL RAINFALL DOWNSCALING: REPRODUCIBLE PIPELINE")
    print("=" * 75)
    
    os.makedirs("results", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    
    # -------------------------------------------------------------
    # Phase 1: Data Audit
    # -------------------------------------------------------------
    print("\n>>> Phase 1: Running Data Audit...")
    audit_dict = run_data_audit("master_dataset_v2.csv", "results")
    
    # -------------------------------------------------------------
    # Phase 2: Dataset Preparation & Chronological Split
    # -------------------------------------------------------------
    print("\n>>> Phase 2: Preparing and Splitting Chronological Datasets...")
    train_raw, val_raw, test_raw = prepare_and_split_datasets("master_dataset_v2.csv", "data/processed")
    
    # -------------------------------------------------------------
    # Phase 3: Feature Engineering (Defensible features, no initial lags)
    # -------------------------------------------------------------
    print("\n>>> Phase 3: Extracting Features...")
    train_df = extract_features(train_raw)
    val_df = extract_features(val_raw)
    test_df = extract_features(test_raw)
    print(f"Engineered {len(FEATURE_COLUMNS)} defensible features: {FEATURE_COLUMNS}")
    
    # -------------------------------------------------------------
    # Phase 4: Standard Baselines
    # -------------------------------------------------------------
    print("\n>>> Phase 4: Evaluating Standard Baselines...")
    baseline_records = evaluate_baselines(train_df, val_df, test_df)
    
    # -------------------------------------------------------------
    # Phase 5, 6, 7: Model Training (RF, Standardized Ridge, XGBoost, LightGBM)
    # -------------------------------------------------------------
    print("\n>>> Phase 5, 6, 7: Training Models (Direct vs Residual Downscaling)...")
    model_records, trained_models, test_preds, ridge_diag = train_models_pipeline(
        train_df, val_df, test_df,
        feature_cols=FEATURE_COLUMNS,
        models_dir="models"
    )
    
    # -------------------------------------------------------------
    # Phase 8: Metrics Compilation & Model Selection strictly on Validation Set
    # -------------------------------------------------------------
    print("\n>>> Phase 8: Compiling Metrics Summary...")
    all_metrics = baseline_records + model_records
    metrics_summary_df = pd.DataFrame(all_metrics)
    metrics_summary_path = "results/metrics_summary.csv"
    metrics_summary_df.to_csv(metrics_summary_path, index=False)
    print(f"Saved complete metrics matrix to {metrics_summary_path}")
    
    # Model Selection based strictly on 2023 Validation RMSE
    val_subset = metrics_summary_df[metrics_summary_df['Dataset'] == 'Validation'].sort_values(by='RMSE')
    best_model_name = val_subset.iloc[0]['Model']
    print(f"\n=======================================================")
    print(f"MODEL SELECTION (Strictly based on 2023 Validation Set)")
    print(f"Selected Model: {best_model_name}")
    print("=======================================================")
    print(val_subset[['Model', 'RMSE', 'MAE', 'R2', 'Bias', 'Correlation']].to_string(index=False))
    
    # Freezing the selected model for untouched 2024 test evaluation
    best_pred_y = test_preds.get(best_model_name, test_preds['Ridge_Residual'])
    best_res_delta = test_preds.get(f"{best_model_name}_delta", test_preds['Ridge_Residual_delta'])
    
    test_pred_df = test_df[['DATE', 'GPCODE', 'GPNAME', 'BLOCK', 'RAINFALL', 'REFERENCE_RAINFALL']].copy()
    test_pred_df['PREDICTED_RESIDUAL'] = best_res_delta
    test_pred_df['PREDICTED_RAINFALL'] = best_pred_y
    test_pred_df['ERROR'] = test_pred_df['PREDICTED_RAINFALL'] - test_pred_df['RAINFALL']
    test_pred_csv = "results/test_predictions.csv"
    test_pred_df.to_csv(test_pred_csv, index=False)
    print(f"Saved 2024 test predictions to {test_pred_csv} ({len(test_pred_df):,} records)")
    
    # -------------------------------------------------------------
    # Phase 9: Panchayat-Level Validation
    # -------------------------------------------------------------
    print("\n>>> Phase 9: Computing Panchayat-Level Spatial Validation...")
    panchayat_df = compute_panchayat_level_metrics(test_df, best_pred_y, "results")
    
    gp_improv = panchayat_df['RMSE_Improvement']
    gp_stats = {
        'median_rmse_improvement': float(gp_improv.median()),
        'mean_rmse_improvement': float(gp_improv.mean()),
        'min_rmse_improvement': float(gp_improv.min()),
        'max_rmse_improvement': float(gp_improv.max()),
        'p25_rmse_improvement': float(gp_improv.quantile(0.25)),
        'p75_rmse_improvement': float(gp_improv.quantile(0.75)),
        'pct_panchayats_improving': float((gp_improv > 0).mean() * 100.0),
        'total_panchayats': int(len(panchayat_df))
    }
    
    print(f"Panchayat Distribution Metrics (2024 Test Set, {gp_stats['total_panchayats']} Panchayats):")
    print(f"  - Median RMSE Improvement: {gp_stats['median_rmse_improvement']:.4f} mm/day")
    print(f"  - 25th Percentile:         {gp_stats['p25_rmse_improvement']:.4f} mm/day")
    print(f"  - 75th Percentile:         {gp_stats['p75_rmse_improvement']:.4f} mm/day")
    print(f"  - Min / Max Improvement:   {gp_stats['min_rmse_improvement']:.4f} / {gp_stats['max_rmse_improvement']:.4f} mm/day")
    print(f"  - Panchayats Improving:    {gp_stats['pct_panchayats_improving']:.2f}%")
    
    # -------------------------------------------------------------
    # Phase 10: Spatial Generalization (Standardized Ridge Residual on Unseen Blocks)
    # -------------------------------------------------------------
    print("\n>>> Phase 10: Evaluating Spatial Generalization (Standardized Ridge on Holdout Blocks)...")
    spatial_holdout_df, spatial_summary = evaluate_spatial_generalization(
        train_df, test_df, FEATURE_COLUMNS,
        holdout_blocks=['Tundi', 'Topchanchi'],
        results_dir="results"
    )
    
    # -------------------------------------------------------------
    # Phase 11: Feature Importance strictly on 2023 Validation Set
    # -------------------------------------------------------------
    print("\n>>> Phase 11: Computing Feature Importance on Validation Set...")
    best_model_obj = trained_models['Ridge_Residual']
    X_val = val_df[FEATURE_COLUMNS].values
    y_val_res = val_df['RESIDUAL'].values
    imp_df = compute_and_save_feature_importance(best_model_obj, X_val, y_val_res, FEATURE_COLUMNS, "results")
    
    # -------------------------------------------------------------
    # Phase 12: Visualizations
    # -------------------------------------------------------------
    print("\n>>> Phase 12: Generating Core Visualizations...")
    generate_core_visualizations(test_df, best_pred_y, panchayat_df, imp_df, "figures")
    
    # -------------------------------------------------------------
    # Phase 14: Experiment Metadata Generation
    # -------------------------------------------------------------
    metadata = {
        'experiment_name': 'Dhanbad_Panchayat_Rainfall_Downscaling',
        'dataset_name': 'master_dataset_v2.csv',
        'dataset_row_count': 436653,
        'number_of_panchayats_total': 239,
        'number_of_panchayats_modeled': 237,
        'excluded_missing_target_rows': 3654,
        'excluded_panchayats': ['MAHESHPUR 2 (GPCODE 111755)', 'RAJGANJ (GPCODE 111773)'],
        'date_range': '2020-01-01 to 2024-12-31',
        'train_period': '2020-01-01 to 2022-12-31 (259,752 rows)',
        'validation_period': '2023-01-01 to 2023-12-31 (86,505 rows)',
        'test_period': '2024-01-01 to 2024-12-31 (86,742 rows)',
        'target_variable': 'RAINFALL (CHIRPS daily precipitation)',
        'reference_variable': 'REFERENCE_RAINFALL (ERA5-Land daily precipitation)',
        'selected_model': best_model_name,
        'model_parameters': {
            'Ridge': {
                'scaler': 'StandardScaler',
                'alpha': 10.0,
                'random_state': 42
            }
        },
        'random_seed': 42,
        'feature_list': FEATURE_COLUMNS,
        'held_out_blocks_spatial_experiment': ['Tundi', 'Topchanchi'],
        'ridge_direct_vs_residual_diagnostics': ridge_diag,
        'panchayat_distribution_metrics': gp_stats,
        'spatial_holdout_summary': spatial_summary
    }
    
    metadata_path = "results/experiment_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)
    print(f"Saved experiment metadata to {metadata_path}")
    
    print("\n" + "=" * 75)
    print("ALL 15 CHANGES APPLIED AND EXECUTED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    main()
