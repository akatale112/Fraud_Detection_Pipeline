"""
Fraud detection feature engineering for Kaggle-style transaction data.
Adds derived columns to a Spark DataFrame for model training.
"""
from pyspark.sql import DataFrame, functions as F

# Base feature names (Kaggle Credit Card schema)
BASE_FEATURES = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]

# Derived feature names added by add_fraud_features
DERIVED_FEATURES = ["log_amount", "time_hour"]

# All numeric feature columns for training (order fixed for reproducibility)
FEATURE_COLUMNS = BASE_FEATURES + DERIVED_FEATURES


def add_fraud_features(df: DataFrame) -> DataFrame:
    """
    Add derived features for fraud detection.
    - log_amount: log(Amount + 1) to reduce skew
    - time_hour: hour-of-day proxy from Time (seconds) for daily pattern
    """
    df = df.withColumn("log_amount", F.log1p(F.col("Amount")))
    # Time in Kaggle is seconds since first txn; 86400 sec = 1 day
    df = df.withColumn("time_hour", (F.col("Time") % 86400) / 3600.0)
    return df
