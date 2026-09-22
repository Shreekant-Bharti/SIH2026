# Panchayat-Level Rainfall Downscaling: Dhanbad District, Jharkhand

## 1. Project Overview & Objective
This repository contains the end-to-end research and implementation pipeline for **Panchayat-Level Daily Rainfall Downscaling** in **Dhanbad District, Jharkhand, India**.

The primary objective is to develop and evaluate a Machine Learning spatial downscaling and residual-correction model that transforms coarse-resolution **ERA5-Land daily rainfall** (~9 km centroid-sampled) into localized, high-resolution **Panchayat-level daily rainfall (CHIRPS reference)** for **239 Panchayats** across **10 administrative blocks** (2020–2024).

---

## 2. Mathematical Formulation

The pipeline utilizes an additive residual downscaling formulation:
$$\text{RESIDUAL} = \text{RAINFALL}_{\text{Observed (CHIRPS)}} - \text{REFERENCE\_RAINFALL}_{\text{Coarse (ERA5-Land)}}$$
$$\widehat{\text{RESIDUAL}} = f_{\boldsymbol{\theta}}(\mathbf{x}_i)$$
$$\widehat{\text{RAINFALL}} = \max\left(0, \text{REFERENCE\_RAINFALL} + \widehat{\text{RESIDUAL}}\right)$$

Where $\mathbf{x}_i$ is a feature vector composed of coarse precipitation, thermodynamic variables, local orography, and seasonal temporal indices.

---

## 3. Strict Chronological Partitioning & Leakage Prevention

To ensure zero look-ahead bias and simulate real-world operational evaluation:
* **Training Set:** `2020-01-01` to `2022-12-31` (3 years, 259,752 records across 237 Panchayats)
* **Validation Set:** `2023-01-01` to `2023-12-31` (1 year, 86,505 records) — **used strictly for model selection, hyperparameter tuning, and feature importance calculation**.
* **Independent Test Set:** `2024-01-01` to `2024-12-31` (1 year, 86,742 records) — **held completely untouched until final benchmark evaluation**.

*Note on Missing Targets:* In `master_dataset_v2.csv`, 3,654 rows have missing `RAINFALL` target values belonging to 2 Panchayats (`MAHESHPUR 2` and `RAJGANJ` in Baghmara block). These rows are preserved in the raw dataset but excluded from supervised training/evaluation. No imputation is applied to target labels.

---

## 4. Directory Structure

```text
.
├── master_dataset_v2.csv          # Raw master dataset (436,653 rows, strictly unmodified)
├── data/
│   ├── raw/                       # Symlink to raw dataset
│   └── processed/
│       ├── train.parquet          # 2020-2022 Train (259,752 records)
│       ├── validation.parquet     # 2023 Validation (86,505 records)
│       └── test.parquet           # 2024 Test (86,742 records)
├── src/
│   ├── __init__.py
│   ├── audit.py                   # Phase 1: Data audit & quality report generator
│   ├── preprocessing.py           # Phase 2: Chronological dataset splitter (Parquet)
│   ├── features.py                # Phase 3: Defensible feature engineering (no initial lags)
│   ├── baselines.py               # Phase 4: Baseline A (ERA5) & Baseline B (Climatology)
│   ├── train.py                   # Phase 5-7: Standardized Ridge, RF, XGBoost, LightGBM
│   ├── evaluate.py                # Phase 8-9: Regression, contingency, and Panchayat metrics
│   ├── generalization.py          # Phase 10-11: Spatial holdout & validation permutation importance
│   └── visualization.py           # Phase 12: Core 6 publication-ready figures
├── models/                        # Serialized model artifacts (.joblib)
├── results/
│   ├── data_audit.csv             # Feature distributions and completeness audit
│   ├── data_quality_report.md     # Markdown audit report
│   ├── experiment_metadata.json   # Machine-readable experiment configuration record
│   ├── metrics_summary.csv        # Comprehensive performance metrics across all models
│   ├── test_predictions.csv       # 2024 test predictions with residuals and errors (86,742 rows)
│   ├── panchayat_metrics.csv      # Panchayat-by-Panchayat spatial validation metrics
│   ├── spatial_generalization.csv # Spatial block holdout benchmark results
│   └── feature_importance.csv     # Permutation importance on 2023 validation set
├── figures/                       # High-resolution PNG visualizations (Phase 12)
│   ├── 1_baseline_vs_observed.png
│   ├── 2_model_vs_observed.png
│   ├── 3_error_distribution.png
│   ├── 4_monthly_monsoon_performance.png
│   ├── 5_feature_importance.png
│   └── 6_panchayat_error_distribution.png
├── run_pipeline.py                # Master 12-phase pipeline runner
├── requirements.txt
└── README.md
```

---

## 5. Summary of Empirical Results

### 5.1 Model Selection on 2023 Validation Set

Models were compared and selected based on **2023 Validation RMSE**:

| Model / Formulation | Validation RMSE (mm) | Validation MAE (mm) | Validation $R^2$ | Validation Correlation ($r$) |
| :--- | :---: | :---: | :---: | :---: |
| **Ridge Residual (Standardized) [SELECTED]** | **6.5444** | **3.5337** | **+0.3986** | **0.6427** |
| Ridge Direct (Standardized) | 6.5445 | 3.5337 | +0.3986 | 0.6427 |
| LightGBM Direct | 6.7366 | 3.4345 | +0.3627 | 0.6324 |
| Baseline A: Coarse ERA5 Reference | 6.8120 | 2.9265 | +0.3484 | 0.6359 |
| XGBoost Residual | 7.0543 | 3.5718 | +0.3012 | 0.6215 |
| LightGBM Residual | 7.0855 | 3.6116 | +0.2950 | 0.6219 |
| Random Forest Direct | 7.2106 | 3.6284 | +0.2699 | 0.5882 |
| XGBoost Direct | 7.2293 | 3.5662 | +0.2661 | 0.5932 |
| Random Forest Residual | 7.4936 | 3.7148 | +0.2115 | 0.5588 |
| Baseline B: Historical Climatology | 8.6333 | 4.5318 | -0.0466 | 0.3409 |

---

### 5.2 Final Performance on Untouched 2024 Test Set (86,742 Records)

The selected Standardized Ridge Residual model was evaluated on the untouched 2024 Test Set:

| Metric | Baseline A (ERA5-Land Reference) | Baseline B (Historical Climatology) | Standardized Ridge Residual | Improvement over ERA5 |
| :--- | :---: | :---: | :---: | :---: |
| **RMSE (mm/day)** | 10.2224 | 8.4695 | **6.6698** | **-34.8% error reduction** |
| **MAE (mm/day)** | 3.7500 | 4.5654 | **3.6738** | **-2.0%** |
| **$R^2$ Score** | -0.4250 | +0.0218 | **+0.3934** | **+0.818 points shift** |
| **Pearson Correlation ($r$)** | 0.5940 | 0.3754 | **0.6434** | **+8.3% coherence** |
| **Mean Bias (mm/day)** | **+0.5044** | +0.7003 | +1.0062 | — |

---

### 5.3 Event Detection Contingency Metrics (2024 Test Set)

| Model | Precipitation Threshold | POD (Recall) | FAR (False Alarm) | CSI (Threat Score) |
| :--- | :---: | :---: | :---: | :---: |
| **Baseline A: Coarse ERA5** | $\ge 0.1\text{ mm}$ (Trace / Rain Event) | 89.6% | 53.0% | **0.446** |
| **Ridge Residual Downscaled** | $\ge 0.1\text{ mm}$ (Trace / Rain Event) | **98.6%** | 65.9% | 0.340 |
| **Baseline A: Coarse ERA5** | $\ge 5.0\text{ mm}$ (Moderate Rain) | 66.3% | **37.9%** | **0.472** |
| **Ridge Residual Downscaled** | $\ge 5.0\text{ mm}$ (Moderate Rain) | **79.7%** | 47.9% | 0.459 |
| **Baseline A: Coarse ERA5** | $\ge 15.0\text{ mm}$ (Heavy / Extreme Rain) | **40.9%** | **39.4%** | **0.323** |
| **Ridge Residual Downscaled** | $\ge 15.0\text{ mm}$ (Heavy / Extreme Rain) | 33.9% | 40.5% | 0.279 |

---

### 5.4 Spatial Generalization Experiment (Held-Out Blocks)

To assess whether the selected Standardized Ridge model transfers across geographic space without spatial memorization, `Tundi` and `Topchanchi` blocks (42 Panchayats, 15,372 test records) were held out completely during training:

| Evaluation Domain (2024 Test Period) | Records | ERA5 Reference RMSE | Ridge Residual RMSE | RMSE Improvement | $R^2$ Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Unseen Holdout Blocks (`Tundi` + `Topchanchi`)** | 15,372 | 8.9801 mm | **6.3920 mm** | **+2.5881 mm (-28.8%)** | **+0.3948** |
| **Seen Training Blocks (8 Blocks)** | 71,370 | 10.4707 mm | **6.7285 mm** | **+3.7422 mm (-35.7%)** | **+0.3931** |

---

### 5.5 Panchayat-Level Spatial Performance Distribution (237 Panchayats)

* **Median Panchayat RMSE Improvement:** **$+3.5965\text{ mm/day}$**
* **25th Percentile Improvement:** $+3.1630\text{ mm/day}$
* **75th Percentile Improvement:** $+4.1169\text{ mm/day}$
* **Min / Max Improvement:** $+1.6702\text{ mm/day}$ / $+4.4982\text{ mm/day}$
* **Percentage of Panchayats Improving over ERA5:** **100.0% (237 / 237 Panchayats)**

---

## 6. Diagnostic: Direct vs. Residual Formulation

The diagnostic in `src/train.py` verified the numerical difference between Ridge Direct and Ridge Residual:
* **Validation Max Absolute Difference:** $0.0078\text{ mm}$ ($7.8\text{ microns}$)
* **Test Max Absolute Difference:** $0.0247\text{ mm}$ ($24.7\text{ microns}$)
* **Reason:** For linear models where `REFERENCE_RAINFALL` is an input feature, predicting rainfall directly versus predicting the residual are affine transformations under unpenalized OLS. Under $L_2$ Ridge shrinkage ($\alpha=10.0$) with standardized features, a minor regularization variance occurs, resulting in near-identical continuous predictions ($\le 0.025\text{ mm}$).

---

## 7. Feature Importance (Validation Set Permutation)

Permutation importance was evaluated strictly on the **2023 Validation Set** ($n=10$ repeats, metric = `neg_RMSE`):
1. **`MONTH` & `DAY_OF_YEAR`:** Monsoonal cycle timing ($\Delta\text{RMSE} \approx +3.25\text{ mm/day}$)
2. **`REFERENCE_RAINFALL` & `LOG_REFERENCE_RAINFALL`:** Primary coarse dynamic forcing ($\Delta\text{RMSE} \approx +2.97\text{ mm/day}$)
3. **`SIN_DOY` & `COS_DOY`:** Cyclical annual progression ($\Delta\text{RMSE} \approx +0.25\text{ mm/day}$)
4. **`ET`, `HUMIDITY`, `WIND`:** Boundary layer moisture flux and convective advection
5. **`ELEVATION` & `SLOPE`:** Static orographic modulation

*Note:* Feature importance represents statistical predictive sensitivity on validation data and must not be interpreted as physical causation.

---

## 8. Methodological Limitations & Realistic Considerations

1. **Continuous vs. Event Metric Trade-off:** While continuous RMSE improves by $34.8\%$, regression models predict small non-zero values on dry days, which raises the False Alarm Ratio ($\text{FAR} = 65.9\%$) for trace precipitation ($\ge 0.1\text{ mm}$).
2. **Heavy Convective Peak Attenuation ($\ge 15\text{ mm}$):** Standard $L_2$ regression regularizes toward the conditional mean, resulting in lower Probability of Detection ($\text{POD} = 33.9\%$) for extreme convective peaks compared to raw ERA5 ($\text{POD} = 40.9\%$).
3. **Operational Forecasting Transition:** To move from historical reanalysis downscaling to operational real-time forecasting, ERA5-Land inputs must be replaced with operational NWP forecasts (e.g., IMD GFS or ECMWF IFS) coupled with a two-stage classifier-regressor to suppress false-positive drizzle.

---

## 9. Quickstart & Pipeline Reproduction

### Installation
```bash
pip install -r requirements.txt
```

### Run Full Pipeline
To execute all 12 phases, train models, run diagnostics, compute metrics, and generate figures:
```bash
python3 run_pipeline.py
```
