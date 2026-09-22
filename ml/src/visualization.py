"""
Phase 12: Visualizations Module
Generates the core 6 publication-ready visualizations with exact dataset period and model labels:
1. Baseline vs observed (ERA5-Land vs CHIRPS, 2024 Test Set)
2. Model vs observed (Ridge Residual vs CHIRPS, 2024 Test Set)
3. Error distribution (Baseline vs Ridge Residual Error, 2024 Test Set, with clipping notation)
4. Monthly / monsoon performance (2024 Test Set)
5. Feature importance (Permutation Importance on 2023 Validation Set)
6. Panchayat error distribution (Panchayat-level RMSE improvement, 2024 Test Set)
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


# Clean styling
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#e0e0e0'
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.alpha'] = 0.7


def generate_core_visualizations(
    test_df: pd.DataFrame,
    y_pred: np.ndarray,
    panchayat_df: pd.DataFrame,
    imp_df: pd.DataFrame,
    figures_dir: str = "figures"
):
    os.makedirs(figures_dir, exist_ok=True)
    
    y_true = test_df['RAINFALL'].values
    ref_rain = test_df['REFERENCE_RAINFALL'].values
    pred_rain = np.clip(y_pred, 0, None)
    
    max_val = max(float(np.percentile(y_true, 99.9)), float(np.percentile(pred_rain, 99.9)), 50.0)
    
    # -------------------------------------------------------------
    # 1. Baseline vs Observed (ERA5-Land Reference vs CHIRPS)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6.5, 5.5), dpi=300)
    hb = ax.hexbin(y_true, ref_rain, gridsize=50, cmap='plasma', mincnt=1, bins='log', extent=[0, max_val, 0, max_val])
    ax.plot([0, max_val], [0, max_val], 'k--', linewidth=1.5, label='1:1 Line')
    cb = fig.colorbar(hb, ax=ax, shrink=0.85)
    cb.set_label('Log10(Count)', fontsize=10)
    ax.set_title('1. Baseline (ERA5-Land) vs Observed (CHIRPS)\n[Independent Test Set — 2024]', fontsize=11, fontweight='bold')
    ax.set_xlabel('Observed Rainfall [CHIRPS] (mm/day)', fontsize=10, fontweight='bold')
    ax.set_ylabel('Coarse Reference Rainfall [ERA5-Land] (mm/day)', fontsize=10, fontweight='bold')
    ax.legend(loc='upper left')
    ax.grid(True)
    plt.tight_layout()
    p1 = os.path.join(figures_dir, "1_baseline_vs_observed.png")
    plt.savefig(p1)
    plt.close()
    print(f"Saved {p1}")
    
    # -------------------------------------------------------------
    # 2. Model vs Observed (Ridge Residual Downscaled vs CHIRPS)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6.5, 5.5), dpi=300)
    hb = ax.hexbin(y_true, pred_rain, gridsize=50, cmap='viridis', mincnt=1, bins='log', extent=[0, max_val, 0, max_val])
    ax.plot([0, max_val], [0, max_val], 'r--', linewidth=1.5, label='1:1 Line')
    cb = fig.colorbar(hb, ax=ax, shrink=0.85)
    cb.set_label('Log10(Count)', fontsize=10)
    ax.set_title('2. Ridge Residual Downscaled vs Observed (CHIRPS)\n[Independent Test Set — 2024]', fontsize=11, fontweight='bold')
    ax.set_xlabel('Observed Rainfall [CHIRPS] (mm/day)', fontsize=10, fontweight='bold')
    ax.set_ylabel('Predicted Rainfall [Ridge Residual] (mm/day)', fontsize=10, fontweight='bold')
    ax.legend(loc='upper left')
    ax.grid(True)
    plt.tight_layout()
    p2 = os.path.join(figures_dir, "2_model_vs_observed.png")
    plt.savefig(p2)
    plt.close()
    print(f"Saved {p2}")
    
    # -------------------------------------------------------------
    # 3. Error Distribution (Prediction Error Comparison)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.5, 5.0), dpi=300)
    ref_err_full = ref_rain - y_true
    ml_err_full = pred_rain - y_true
    
    # Clipped for display only
    ref_err_clip = np.clip(ref_err_full, -25, 25)
    ml_err_clip = np.clip(ml_err_full, -25, 25)
    
    sns.kdeplot(ref_err_clip, ax=ax, label=f'Baseline Error (Mean: {np.mean(ref_err_full):.2f}, Std: {np.std(ref_err_full):.2f} mm/day)', color='#d95f02', linewidth=2)
    sns.kdeplot(ml_err_clip, ax=ax, label=f'Ridge Residual Error (Mean: {np.mean(ml_err_full):.2f}, Std: {np.std(ml_err_full):.2f} mm/day)', color='#1b9e77', linewidth=2.2)
    ax.axvline(0, color='black', linestyle=':', alpha=0.8)
    ax.set_title('3. Prediction Error Distribution: Baseline vs Ridge Residual\n[Independent Test Set — 2024]', fontsize=11, fontweight='bold')
    ax.set_xlabel('Prediction Error [Predicted - Observed] (mm/day)', fontsize=10, fontweight='bold')
    ax.set_ylabel('Density', fontsize=10)
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True)
    # Explicit clipping note
    ax.text(0.5, -0.16, "*Density visualization is clipped at ±25 mm/day for clarity; all summary statistics use the full unclipped error distribution.",
            ha='center', va='center', transform=ax.transAxes, fontsize=8, color='#555555', style='italic')
    plt.tight_layout()
    p3 = os.path.join(figures_dir, "3_error_distribution.png")
    plt.savefig(p3)
    plt.close()
    print(f"Saved {p3}")
    
    # -------------------------------------------------------------
    # 4. Monthly / Monsoon Performance
    # -------------------------------------------------------------
    df_eval = test_df.copy()
    df_eval['PRED'] = pred_rain
    df_eval['MONTH_NAME'] = df_eval['DATE'].dt.strftime('%b')
    df_eval['MONTH_NUM'] = df_eval['DATE'].dt.month
    
    monthly = df_eval.groupby(['MONTH_NUM', 'MONTH_NAME'])[['RAINFALL', 'REFERENCE_RAINFALL', 'PRED']].mean().reset_index()
    monthly = monthly.sort_values(by='MONTH_NUM')
    
    fig, ax = plt.subplots(figsize=(9.5, 4.8), dpi=300)
    x = np.arange(len(monthly))
    w = 0.26
    ax.bar(x - w, monthly['RAINFALL'], w, label='Observed (CHIRPS)', color='#2ca02c', alpha=0.9)
    ax.bar(x, monthly['REFERENCE_RAINFALL'], w, label='Reference (ERA5-Land)', color='#ff7f0e', alpha=0.85)
    ax.bar(x + w, monthly['PRED'], w, label='Ridge Residual Downscaled', color='#1f77b4', alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(monthly['MONTH_NAME'], fontsize=10, fontweight='bold')
    ax.set_ylabel('Mean Rainfall (mm/day)', fontsize=10, fontweight='bold')
    ax.set_title('4. Monthly & Monsoon Mean Rainfall Comparison\n[Independent Test Set — 2024]', fontsize=11, fontweight='bold')
    ax.legend(frameon=True)
    ax.grid(axis='y')
    plt.tight_layout()
    p4 = os.path.join(figures_dir, "4_monthly_monsoon_performance.png")
    plt.savefig(p4)
    plt.close()
    print(f"Saved {p4}")
    
    # -------------------------------------------------------------
    # 5. Feature Importance (Permutation on 2023 Validation Set)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8.5, 5.2), dpi=300)
    imp_col = 'Permutation_Importance_Val_Mean' if 'Permutation_Importance_Val_Mean' in imp_df.columns else imp_df.columns[1]
    top_imp = imp_df.head(12).sort_values(by=imp_col, ascending=True)
    
    bars = ax.barh(top_imp['Feature'], top_imp[imp_col], color='#2b83ba', height=0.65)
    for b in bars:
        w_val = b.get_width()
        offset = 0.01 if w_val >= 0 else -0.05
        ax.text(w_val + offset, b.get_y() + b.get_height()/2, f"{w_val:.3f}", va='center', fontsize=8.5)
        
    ax.axvline(0, color='black', linewidth=0.8, linestyle='--')
    ax.set_xlabel('Permutation Feature Importance (Mean ΔRMSE in mm/day)', fontsize=10, fontweight='bold')
    ax.set_title('5. Permutation Importance — Validation Set (2023)\n[Standardized Ridge Residual Model, n_repeats=10]', fontsize=11, fontweight='bold')
    ax.grid(axis='x')
    plt.tight_layout()
    p5 = os.path.join(figures_dir, "5_feature_importance.png")
    plt.savefig(p5)
    plt.close()
    print(f"Saved {p5}")
    
    # -------------------------------------------------------------
    # 6. Panchayat Error Distribution
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.5, 5.0), dpi=300)
    sns.histplot(panchayat_df['RMSE_Improvement'], kde=True, ax=ax, color='#2b83ba', bins=25)
    ax.axvline(0, color='red', linestyle='--', label='Zero Improvement Line')
    ax.axvline(panchayat_df['RMSE_Improvement'].median(), color='green', linestyle='-',
               label=f"Median Improvement: {panchayat_df['RMSE_Improvement'].median():.3f} mm/day")
    ax.set_title('6. Panchayat-Level RMSE Improvement (237 Panchayats)\n[Independent Test Set — 2024]', fontsize=11, fontweight='bold')
    ax.set_xlabel('RMSE Improvement [ERA5 Reference RMSE - ML Model RMSE] (mm/day)', fontsize=10, fontweight='bold')
    ax.set_ylabel('Number of Panchayats', fontsize=10)
    ax.legend(loc='upper right')
    ax.grid(True)
    plt.tight_layout()
    p6 = os.path.join(figures_dir, "6_panchayat_error_distribution.png")
    plt.savefig(p6)
    plt.close()
    print(f"Saved {p6}")
