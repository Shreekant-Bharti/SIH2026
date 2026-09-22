"""
Phase 8 & 9: Evaluation and Panchayat Validation Module
Computes regression metrics, event contingency metrics (POD, FAR, CSI @ 0.1, 5, 15 mm),
and Panchayat-level spatial validation metrics.
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def compute_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Computes MAE, RMSE, R2, Bias, and Pearson Correlation.
    """
    y_pred_clipped = np.clip(y_pred, 0, None)
    mae = mean_absolute_error(y_true, y_pred_clipped)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred_clipped))
    r2 = r2_score(y_true, y_pred_clipped)
    bias = np.mean(y_pred_clipped - y_true)
    
    if np.std(y_true) > 1e-8 and np.std(y_pred_clipped) > 1e-8:
        corr = float(np.corrcoef(y_true, y_pred_clipped)[0, 1])
    else:
        corr = 0.0
        
    return {
        'MAE': float(mae),
        'RMSE': float(rmse),
        'R2': float(r2),
        'Bias': float(bias),
        'Correlation': corr
    }


def compute_contingency_metrics(y_true: np.ndarray, y_pred: np.ndarray, threshold: float) -> Dict[str, float]:
    """
    Calculates POD, FAR, and CSI for precipitation threshold.
    """
    y_pred_clipped = np.clip(y_pred, 0, None)
    obs_event = (y_true >= threshold)
    pred_event = (y_pred_clipped >= threshold)
    
    hits = np.sum(obs_event & pred_event)
    misses = np.sum(obs_event & (~pred_event))
    false_alarms = np.sum((~obs_event) & pred_event)
    
    pod = hits / (hits + misses) if (hits + misses) > 0 else 0.0
    far = false_alarms / (hits + false_alarms) if (hits + false_alarms) > 0 else 0.0
    csi = hits / (hits + misses + false_alarms) if (hits + misses + false_alarms) > 0 else 0.0
    
    return {
        f'POD_{threshold}': float(pod),
        f'FAR_{threshold}': float(far),
        f'CSI_{threshold}': float(csi)
    }


def evaluate_model_performance(
    model_name: str,
    dataset_name: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    thresholds: List[float] = [0.1, 5.0, 15.0]
) -> Dict[str, Any]:
    """
    Combines regression and contingency metrics into a single record.
    """
    reg = compute_regression_metrics(y_true, y_pred)
    res = {
        'Model': model_name,
        'Dataset': dataset_name,
        **reg
    }
    for th in thresholds:
        cont = compute_contingency_metrics(y_true, y_pred, th)
        res.update(cont)
    return res


def compute_panchayat_level_metrics(
    test_df: pd.DataFrame,
    y_pred: np.ndarray,
    results_dir: str = "results"
) -> pd.DataFrame:
    """
    Computes performance separately for each Panchayat (GPCODE) on the test set.
    Outputs: results/panchayat_metrics.csv
    """
    os.makedirs(results_dir, exist_ok=True)
    df = test_df.copy()
    df['PREDICTED_RAINFALL'] = np.clip(y_pred, 0, None)
    
    records = []
    for (gpcode, gpname, block), group in df.groupby(['GPCODE', 'GPNAME', 'BLOCK']):
        yt = group['RAINFALL'].values
        yp = group['PREDICTED_RAINFALL'].values
        ref = group['REFERENCE_RAINFALL'].values
        
        ml_reg = compute_regression_metrics(yt, yp)
        ref_reg = compute_regression_metrics(yt, ref)
        
        records.append({
            'GPCODE': gpcode,
            'GPNAME': gpname,
            'BLOCK': block,
            'N_Days': len(group),
            'ML_MAE': ml_reg['MAE'],
            'ML_RMSE': ml_reg['RMSE'],
            'ML_R2': ml_reg['R2'],
            'ML_Bias': ml_reg['Bias'],
            'ML_Correlation': ml_reg['Correlation'],
            'REF_MAE': ref_reg['MAE'],
            'REF_RMSE': ref_reg['RMSE'],
            'REF_Bias': ref_reg['Bias'],
            'REF_Correlation': ref_reg['Correlation'],
            'RMSE_Improvement': ref_reg['RMSE'] - ml_reg['RMSE'],
            'MAE_Improvement': ref_reg['MAE'] - ml_reg['MAE']
        })
        
    panchayat_df = pd.DataFrame(records)
    out_path = os.path.join(results_dir, "panchayat_metrics.csv")
    panchayat_df.to_csv(out_path, index=False)
    print(f"Saved Panchayat validation metrics to {out_path} ({len(panchayat_df)} Panchayats)")
    return panchayat_df
