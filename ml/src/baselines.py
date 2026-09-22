"""
Phase 4: Baselines Module
Implements Baseline A (Coarse ERA5-Land Reference) and Baseline B (Historical Panchayat Climatology).
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any
from src.evaluate import evaluate_model_performance


def evaluate_baselines(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame
) -> List[Dict[str, Any]]:
    """
    Evaluates Baseline A (ERA5-Land) across Train, Val, Test.
    Evaluates Baseline B (Historical Climatology) strictly on Validation and Test to avoid in-sample bias.
    """
    baseline_records = []
    
    # -----------------------------------------------------------------
    # Baseline A: Coarse ERA5-Land Reference Rainfall
    # -----------------------------------------------------------------
    for split_name, df in [('Train', train_df), ('Validation', val_df), ('Test', test_df)]:
        metrics = evaluate_model_performance(
            model_name='Baseline_A_Coarse_ERA5',
            dataset_name=split_name,
            y_true=df['RAINFALL'].values,
            y_pred=df['REFERENCE_RAINFALL'].values
        )
        baseline_records.append(metrics)
        
    # -----------------------------------------------------------------
    # Baseline B: Simple Historical Climatology (Panchayat + DOY mean from TRAIN ONLY)
    # Evaluated ONLY on Validation and Test sets to avoid in-sample train score bias.
    # -----------------------------------------------------------------
    hist_gp_doy = train_df.groupby(['GPCODE', 'DAY_OF_YEAR'])['RAINFALL'].mean().reset_index()
    hist_gp_doy = hist_gp_doy.rename(columns={'RAINFALL': 'HISTORICAL_PRED'})
    
    global_doy = train_df.groupby('DAY_OF_YEAR')['RAINFALL'].mean().to_dict()
    global_mean = float(train_df['RAINFALL'].mean())
    
    for split_name, df in [('Validation', val_df), ('Test', test_df)]:
        merged = pd.merge(df[['GPCODE', 'DAY_OF_YEAR', 'RAINFALL']], hist_gp_doy, on=['GPCODE', 'DAY_OF_YEAR'], how='left')
        missing_mask = merged['HISTORICAL_PRED'].isnull()
        if missing_mask.sum() > 0:
            fallback = merged.loc[missing_mask, 'DAY_OF_YEAR'].map(global_doy).fillna(global_mean)
            merged.loc[missing_mask, 'HISTORICAL_PRED'] = fallback
            
        metrics = evaluate_model_performance(
            model_name='Baseline_B_Historical_Climatology',
            dataset_name=split_name,
            y_true=merged['RAINFALL'].values,
            y_pred=merged['HISTORICAL_PRED'].values
        )
        baseline_records.append(metrics)
        
    return baseline_records
