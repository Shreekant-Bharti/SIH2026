"""
Phase 3: Feature Engineering Module
Constructs defensible meteorological, spatial, temporal, and reference-rainfall features.
Strictly excludes observed rainfall lag features in initial baseline/model phase.
"""

import numpy as np
import pandas as pd
from typing import List


# Standard Defensible Feature Names
FEATURE_COLUMNS = [
    # Meteorological
    'TEMPERATURE',
    'HUMIDITY',
    'WIND',
    'ET',
    # Spatial / Orographic
    'ELEVATION',
    'SLOPE',
    'LANDCOVER',
    # Temporal / Seasonal
    'MONTH',
    'DAY_OF_YEAR',
    'SIN_DOY',
    'COS_DOY',
    'MONSOON_FLAG',
    # Reference Rainfall Properties
    'REFERENCE_RAINFALL',
    'LOG_REFERENCE_RAINFALL',
    'REFERENCE_RAIN_EVENT'
]


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes temporal, reference rainfall transformations, and returns dataframe with all feature columns.
    """
    df = df.copy()
    
    # Ensure DATE is datetime
    if not pd.api.types.is_datetime64_any_dtype(df['DATE']):
        df['DATE'] = pd.to_datetime(df['DATE'])
        
    # Temporal Features
    df['MONTH'] = df['DATE'].dt.month
    df['DAY_OF_YEAR'] = df['DATE'].dt.dayofyear
    df['SIN_DOY'] = np.sin(2 * np.pi * df['DAY_OF_YEAR'] / 365.25)
    df['COS_DOY'] = np.cos(2 * np.pi * df['DAY_OF_YEAR'] / 365.25)
    
    # Monsoon Season Indicator (JJAS: June, July, August, September)
    df['MONSOON_FLAG'] = df['MONTH'].isin([6, 7, 8, 9]).astype(int)
    
    # Reference Rainfall Transformations
    df['LOG_REFERENCE_RAINFALL'] = np.log1p(np.maximum(0, df['REFERENCE_RAINFALL']))
    df['REFERENCE_RAIN_EVENT'] = (df['REFERENCE_RAINFALL'] >= 0.1).astype(float)
    
    return df
