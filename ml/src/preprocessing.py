"""
Phase 2: Dataset Preparation & Chronological Splitter Module
Creates reproducible train, validation, and test parquet files without future leakage.
Outputs: data/processed/train.parquet, validation.parquet, test.parquet
"""

import os
import pandas as pd
import numpy as np
from typing import Tuple


def prepare_and_split_datasets(
    csv_path: str = "master_dataset_v2.csv",
    output_dir: str = "data/processed"
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Loads raw dataset, excludes missing target rows for modeling,
    splits chronologically, and saves parquet files.
    """
    os.makedirs(output_dir, exist_ok=True)
    print(f"Loading raw dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Parse date and sort
    df['DATE'] = pd.to_datetime(df['DATE'])
    df = df.sort_values(by=['DATE', 'GPCODE']).reset_index(drop=True)
    
    # Filter valid target rows for model training & evaluation
    valid_df = df.dropna(subset=['RAINFALL']).copy().reset_index(drop=True)
    
    # Add target residual: Residual = Observed Rainfall - Reference Rainfall
    valid_df['RESIDUAL'] = valid_df['RAINFALL'] - valid_df['REFERENCE_RAINFALL']
    
    # Chronological masks
    train_mask = (valid_df['DATE'] >= '2020-01-01') & (valid_df['DATE'] <= '2022-12-31')
    val_mask = (valid_df['DATE'] >= '2023-01-01') & (valid_df['DATE'] <= '2023-12-31')
    test_mask = (valid_df['DATE'] >= '2024-01-01') & (valid_df['DATE'] <= '2024-12-31')
    
    train_df = valid_df[train_mask].copy().reset_index(drop=True)
    val_df = valid_df[val_mask].copy().reset_index(drop=True)
    test_df = valid_df[test_mask].copy().reset_index(drop=True)
    
    # Validation checks
    assert len(train_df) > 0, "Train split is empty"
    assert len(val_df) > 0, "Validation split is empty"
    assert len(test_df) > 0, "Test split is empty"
    assert train_df['DATE'].max() < val_df['DATE'].min(), "Temporal overlap between Train and Val"
    assert val_df['DATE'].max() < test_df['DATE'].min(), "Temporal overlap between Val and Test"
    
    # Save to parquet
    train_path = os.path.join(output_dir, "train.parquet")
    val_path = os.path.join(output_dir, "validation.parquet")
    test_path = os.path.join(output_dir, "test.parquet")
    
    train_df.to_parquet(train_path, index=False)
    val_df.to_parquet(val_path, index=False)
    test_df.to_parquet(test_path, index=False)
    
    print(f"Saved {train_path} ({len(train_df):,} records, {train_df['GPCODE'].nunique()} Panchayats)")
    print(f"Saved {val_path} ({len(val_df):,} records, {val_df['GPCODE'].nunique()} Panchayats)")
    print(f"Saved {test_path} ({len(test_df):,} records, {test_df['GPCODE'].nunique()} Panchayats)")
    
    return train_df, val_df, test_df


if __name__ == "__main__":
    prepare_and_split_datasets()
