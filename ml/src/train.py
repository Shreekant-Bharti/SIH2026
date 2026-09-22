"""
Phase 5, 6 & 7: Model Training and Residual Downscaling Pipeline
Trains Random Forest (Direct & Residual), Standardized Ridge, XGBoost, and LightGBM models.
Saves models to models/ and records Train, Val, Test metrics.
Includes explicit diagnostics comparing Ridge Direct vs Ridge Residual.
"""

import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import lightgbm as lgb

from src.evaluate import evaluate_model_performance


def train_models_pipeline(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: List[str],
    models_dir: str = "models"
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, np.ndarray], Dict[str, Any]]:
    """
    Trains models in both Direct and Residual Downscaling formulations.
    Standardizes Ridge with StandardScaler.
    Performs Ridge Direct vs Residual diagnostics on Validation and Test data.
    """
    os.makedirs(models_dir, exist_ok=True)
    
    X_train = train_df[feature_cols].values
    y_train_direct = train_df['RAINFALL'].values
    y_train_residual = train_df['RESIDUAL'].values
    ref_train = train_df['REFERENCE_RAINFALL'].values
    
    X_val = val_df[feature_cols].values
    y_val_direct = val_df['RAINFALL'].values
    y_val_residual = val_df['RESIDUAL'].values
    ref_val = val_df['REFERENCE_RAINFALL'].values
    
    X_test = test_df[feature_cols].values
    y_test_direct = test_df['RAINFALL'].values
    y_test_residual = test_df['RESIDUAL'].values
    ref_test = test_df['REFERENCE_RAINFALL'].values
    
    # Model specifications with StandardScaler for Ridge
    models_to_train = [
        ('RandomForest', lambda: RandomForestRegressor(
            n_estimators=100, max_depth=14, min_samples_leaf=4, n_jobs=-1, random_state=42
        )),
        ('Ridge', lambda: Pipeline([
            ('scaler', StandardScaler()),
            ('ridge', Ridge(alpha=10.0, random_state=42))
        ])),
        ('XGBoost', lambda: xgb.XGBRegressor(
            n_estimators=250, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.8,
            n_jobs=-1, random_state=42, tree_method='hist'
        )),
        ('LightGBM', lambda: lgb.LGBMRegressor(
            n_estimators=300, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8,
            n_jobs=-1, random_state=42, verbose=-1
        ))
    ]
    
    all_metrics = []
    trained_models = {}
    test_predictions = {}
    ridge_diagnostics = {}
    
    for model_name, factory in models_to_train:
        print(f"\n--- Training {model_name} ---")
        
        # 1. Direct Formulation (Predict RAINFALL)
        print(f"[{model_name}] Fitting Direct formulation...")
        m_dir = factory()
        m_dir.fit(X_train, y_train_direct)
        
        p_train_dir = np.clip(m_dir.predict(X_train), 0, None)
        p_val_dir = np.clip(m_dir.predict(X_val), 0, None)
        p_test_dir = np.clip(m_dir.predict(X_test), 0, None)
        
        rec_train_dir = evaluate_model_performance(f"{model_name}_Direct", "Train", y_train_direct, p_train_dir)
        rec_val_dir = evaluate_model_performance(f"{model_name}_Direct", "Validation", y_val_direct, p_val_dir)
        rec_test_dir = evaluate_model_performance(f"{model_name}_Direct", "Test", y_test_direct, p_test_dir)
        
        all_metrics.extend([rec_train_dir, rec_val_dir, rec_test_dir])
        joblib.dump(m_dir, os.path.join(models_dir, f"{model_name}_direct.joblib"))
        
        # 2. Residual Downscaling Formulation (Predict RESIDUAL)
        print(f"[{model_name}] Fitting Residual Downscaling formulation...")
        m_res = factory()
        m_res.fit(X_train, y_train_residual)
        
        r_train_pred = m_res.predict(X_train)
        r_val_pred = m_res.predict(X_val)
        r_test_pred = m_res.predict(X_test)
        
        p_train_res = np.clip(ref_train + r_train_pred, 0, None)
        p_val_res = np.clip(ref_val + r_val_pred, 0, None)
        p_test_res = np.clip(ref_test + r_test_pred, 0, None)
        
        rec_train_res = evaluate_model_performance(f"{model_name}_Residual", "Train", y_train_direct, p_train_res)
        rec_val_res = evaluate_model_performance(f"{model_name}_Residual", "Validation", y_val_direct, p_val_res)
        rec_test_res = evaluate_model_performance(f"{model_name}_Residual", "Test", y_test_direct, p_test_res)
        
        all_metrics.extend([rec_train_res, rec_val_res, rec_test_res])
        joblib.dump(m_res, os.path.join(models_dir, f"{model_name}_residual.joblib"))
        
        trained_models[f"{model_name}_Direct"] = m_dir
        trained_models[f"{model_name}_Residual"] = m_res
        
        test_predictions[f"{model_name}_Direct"] = p_test_dir
        test_predictions[f"{model_name}_Residual"] = p_test_res
        test_predictions[f"{model_name}_Residual_delta"] = r_test_pred
        
        # Diagnostic check for Ridge Direct vs Residual
        if model_name == "Ridge":
            val_max_abs_diff = float(np.max(np.abs(p_val_dir - p_val_res)))
            val_mean_abs_diff = float(np.mean(np.abs(p_val_dir - p_val_res)))
            val_array_equal = bool(np.array_equal(p_val_dir, p_val_res))
            val_allclose = bool(np.allclose(p_val_dir, p_val_res, atol=1e-4))
            
            test_max_abs_diff = float(np.max(np.abs(p_test_dir - p_test_res)))
            test_mean_abs_diff = float(np.mean(np.abs(p_test_dir - p_test_res)))
            test_array_equal = bool(np.array_equal(p_test_dir, p_test_res))
            test_allclose = bool(np.allclose(p_test_dir, p_test_res, atol=1e-4))
            
            ridge_direct_coef = m_dir.named_steps['ridge'].coef_
            ridge_residual_coef = m_res.named_steps['ridge'].coef_
            ridge_direct_intercept = float(m_dir.named_steps['ridge'].intercept_)
            ridge_residual_intercept = float(m_res.named_steps['ridge'].intercept_)
            
            ref_idx = feature_cols.index('REFERENCE_RAINFALL') if 'REFERENCE_RAINFALL' in feature_cols else None
            
            ridge_diagnostics = {
                'val_max_abs_difference': val_max_abs_diff,
                'val_mean_abs_difference': val_mean_abs_diff,
                'val_exact_equality': val_array_equal,
                'val_numerical_equality_allclose': val_allclose,
                'test_max_abs_difference': test_max_abs_diff,
                'test_mean_abs_difference': test_mean_abs_diff,
                'test_exact_equality': test_array_equal,
                'test_numerical_equality_allclose': test_allclose,
                'direct_intercept': ridge_direct_intercept,
                'residual_intercept': ridge_residual_intercept,
                'reference_rainfall_feature_index': ref_idx,
                'feature_names': feature_cols,
                'direct_coefficients': ridge_direct_coef.tolist(),
                'residual_coefficients': ridge_residual_coef.tolist()
            }
            
            print("\n=======================================================")
            print("DIAGNOSTIC: Ridge Direct vs Residual Comparison")
            print("=======================================================")
            print(f"Validation Max Absolute Difference:  {val_max_abs_diff:.6f} mm")
            print(f"Validation Mean Absolute Difference: {val_mean_abs_diff:.6f} mm")
            print(f"Validation Exact Equality:           {val_array_equal}")
            print(f"Validation Numerical Equality:       {val_allclose}")
            print(f"Test Set Max Absolute Difference:    {test_max_abs_diff:.6f} mm")
            print(f"Test Set Mean Absolute Difference:   {test_mean_abs_diff:.6f} mm")
            print(f"Test Set Exact Equality:             {test_array_equal}")
            print(f"Test Set Numerical Equality:         {test_allclose}")
            print("=======================================================\n")
            
        print(f"  Validation RMSE: Direct={rec_val_dir['RMSE']:.4f} | Residual={rec_val_res['RMSE']:.4f}")
        print(f"  Test RMSE:       Direct={rec_test_dir['RMSE']:.4f} | Residual={rec_test_res['RMSE']:.4f}")
        
    return all_metrics, trained_models, test_predictions, ridge_diagnostics
