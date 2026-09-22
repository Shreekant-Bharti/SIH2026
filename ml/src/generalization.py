"""
Phase 10 & 11: Spatial Generalization and Feature Importance Module
Evaluates unseen spatial block holdout generalization using the selected standardized Ridge model.
Computes permutation importance strictly on the 2023 Validation Set (zero test data leakage).
Outputs: results/feature_importance.csv and results/spatial_generalization.csv
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.inspection import permutation_importance

from src.evaluate import evaluate_model_performance, compute_regression_metrics


def evaluate_spatial_generalization(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: List[str],
    holdout_blocks: List[str] = ['Tundi', 'Topchanchi'],
    results_dir: str = "results"
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Phase 10: Spatial Generalization Experiment.
    Evaluates the SAME selected model architecture (Standardized Ridge Residual, alpha=10.0).
    Trains ONLY on training-period (2020-2022) data from blocks excluding holdout_blocks.
    Evaluates on unseen holdout blocks in the 2024 test period.
    """
    os.makedirs(results_dir, exist_ok=True)
    
    # 1. Filter training and test partitions by spatial blocks
    train_seen = train_df[~train_df['BLOCK'].isin(holdout_blocks)].copy()
    test_unseen = test_df[test_df['BLOCK'].isin(holdout_blocks)].copy()
    test_seen = test_df[~test_df['BLOCK'].isin(holdout_blocks)].copy()
    
    n_train_panchayats = train_seen['GPCODE'].nunique()
    n_heldout_panchayats = test_unseen['GPCODE'].nunique()
    n_test_records = len(test_unseen)
    
    X_train = train_seen[feature_cols].values
    y_train_res = train_seen['RESIDUAL'].values
    
    # Train Standardized Ridge Residual model
    spatial_ridge = Pipeline([
        ('scaler', StandardScaler()),
        ('ridge', Ridge(alpha=10.0, random_state=42))
    ])
    spatial_ridge.fit(X_train, y_train_res)
    
    # Evaluate on unseen holdout blocks (2024 test period)
    y_true_unseen = test_unseen['RAINFALL'].values
    ref_unseen = test_unseen['REFERENCE_RAINFALL'].values
    pred_res_unseen = spatial_ridge.predict(test_unseen[feature_cols].values)
    pred_rain_unseen = np.clip(ref_unseen + pred_res_unseen, 0, None)
    
    m_ref_unseen = evaluate_model_performance("Baseline_ERA5", "Unseen_Blocks_2024", y_true_unseen, ref_unseen)
    m_ml_unseen = evaluate_model_performance("Ridge_Residual_Spatial_Holdout", "Unseen_Blocks_2024", y_true_unseen, pred_rain_unseen)
    
    # Evaluate on seen blocks (2024 test period)
    y_true_seen = test_seen['RAINFALL'].values
    ref_seen = test_seen['REFERENCE_RAINFALL'].values
    pred_res_seen = spatial_ridge.predict(test_seen[feature_cols].values)
    pred_rain_seen = np.clip(ref_seen + pred_res_seen, 0, None)
    
    m_ref_seen = evaluate_model_performance("Baseline_ERA5", "Seen_Blocks_2024", y_true_seen, ref_seen)
    m_ml_seen = evaluate_model_performance("Ridge_Residual_Spatial_Holdout", "Seen_Blocks_2024", y_true_seen, pred_rain_seen)
    
    res_df = pd.DataFrame([m_ref_unseen, m_ml_unseen, m_ref_seen, m_ml_seen])
    out_csv = os.path.join(results_dir, "spatial_generalization.csv")
    res_df.to_csv(out_csv, index=False)
    
    spatial_summary = {
        'n_train_panchayats': int(n_train_panchayats),
        'n_heldout_panchayats': int(n_heldout_panchayats),
        'heldout_blocks': holdout_blocks,
        'n_test_records': int(n_test_records),
        'era5_unseen_rmse': float(m_ref_unseen['RMSE']),
        'ridge_unseen_rmse': float(m_ml_unseen['RMSE']),
        'rmse_improvement': float(m_ref_unseen['RMSE'] - m_ml_unseen['RMSE']),
        'unseen_mae': float(m_ml_unseen['MAE']),
        'unseen_r2': float(m_ml_unseen['R2']),
        'unseen_correlation': float(m_ml_unseen['Correlation'])
    }
    
    print("\n=======================================================")
    print("PHASE 10: SPATIAL GENERALIZATION (Ridge Residual)")
    print("=======================================================")
    print(f"Held-out Blocks:        {holdout_blocks}")
    print(f"Training Panchayats:    {n_train_panchayats}")
    print(f"Held-out Panchayats:    {n_heldout_panchayats}")
    print(f"Test Records:           {n_test_records:,}")
    print(f"ERA5 Reference RMSE:    {m_ref_unseen['RMSE']:.4f} mm")
    print(f"Ridge Residual RMSE:    {m_ml_unseen['RMSE']:.4f} mm")
    print(f"RMSE Improvement:       {spatial_summary['rmse_improvement']:.4f} mm")
    print(f"R2 Score:               {m_ml_unseen['R2']:.4f}")
    print(f"Correlation:            {m_ml_unseen['Correlation']:.4f}")
    print("=======================================================\n")
    
    return res_df, spatial_summary


def compute_and_save_feature_importance(
    model,
    X_val: np.ndarray,
    y_val_res: np.ndarray,
    feature_names: List[str],
    results_dir: str = "results"
) -> pd.DataFrame:
    """
    Phase 11: Feature Importance using Permutation Importance strictly on the 2023 VALIDATION SET.
    Guarantees ZERO test set leakage.
    Outputs: results/feature_importance.csv
    """
    os.makedirs(results_dir, exist_ok=True)
    
    print("\n=======================================================")
    print("PHASE 11: FEATURE IMPORTANCE (Permutation on 2023 Val Set)")
    print("Feature importance calculated on validation data (2023), not test data.")
    print("=======================================================")
    
    # 1. Intrinsic importance (Standardized Ridge absolute coefficients or Tree importances)
    if hasattr(model, 'named_steps') and 'ridge' in model.named_steps:
        raw_coefs = np.abs(model.named_steps['ridge'].coef_)
        norm_imp = (raw_coefs / np.sum(raw_coefs)) * 100.0
    elif hasattr(model, 'feature_importances_'):
        raw_imp = model.feature_importances_
        norm_imp = (raw_imp / np.sum(raw_imp)) * 100.0
    else:
        norm_imp = np.zeros(len(feature_names))
        
    # 2. Permutation Importance strictly on Validation Data (2023)
    X_eval = X_val
    y_eval = y_val_res
    
    np.random.seed(42)
    sample_size = min(15000, len(X_eval))
    sample_idx = np.random.choice(len(X_eval), size=sample_size, replace=False)
    
    perm = permutation_importance(
        model, X_eval[sample_idx], y_eval[sample_idx],
        n_repeats=10, random_state=42, n_jobs=-1, scoring='neg_root_mean_squared_error'
    )
    
    imp_df = pd.DataFrame({
        'Feature': feature_names,
        'Standardized_Coefficient_Magnitude_Pct': norm_imp,
        'Permutation_Importance_Val_Mean': perm.importances_mean,
        'Permutation_Importance_Val_Std': perm.importances_std
    }).sort_values(by='Permutation_Importance_Val_Mean', ascending=False).reset_index(drop=True)
    
    out_path = os.path.join(results_dir, "feature_importance.csv")
    imp_df.to_csv(out_path, index=False)
    print(f"Saved validation feature importance to {out_path}")
    print(imp_df.to_string(index=False))
    return imp_df
