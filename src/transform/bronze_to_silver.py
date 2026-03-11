"""
Bronze → Silver transformation: clean, validate, deduplicate.
Reads from bronze_transactions, writes to silver_transactions (managed table).
"""
from typing import Optional

from pyspark.sql import SparkSession, DataFrame, functions as F

from src.ingestion.batch_ingest import load_config


def run_bronze_to_silver(
    spark: SparkSession,
    config_path: str,
    env: Optional[str] = "dev",
) -> int:
    cfg = load_config(config_path)
    databricks_cfg = cfg.get("databricks", {})
    tables_cfg = cfg.get("tables", {})

    catalog = databricks_cfg.get("catalog", "")
    schema = databricks_cfg.get("schema")
    if not schema:
        raise ValueError("databricks.schema is not set in config")

    bronze_table = tables_cfg.get("bronze_transactions", "bronze_transactions")
    silver_table = tables_cfg.get("silver_transactions", "silver_transactions")
    full_db = f"{catalog}.{schema}" if catalog else schema
    bronze_full = f"{full_db}.{bronze_table}"
    silver_full = f"{full_db}.{silver_table}"

    df: DataFrame = spark.table(bronze_full)

    # Cast numeric types (Kaggle: Time int, V1–V28 float, Amount float, Class int)
    for i in range(1, 29):
        df = df.withColumn(f"V{i}", F.col(f"V{i}").cast("double"))
    df = (
        df.withColumn("Time", F.col("Time").cast("int"))
        .withColumn("Amount", F.col("Amount").cast("double"))
        .withColumn("Class", F.col("Class").cast("int"))
    )

    # Completeness: drop rows with null in key columns
    df = df.dropna(subset=["Time", "Amount", "Class"])

    # Validity: Amount > 0, Class in (0, 1)
    df = df.filter((F.col("Amount") > 0) & (F.col("Class").isin(0, 1)))

    # Deduplicate: Kaggle has no transaction_id; use (Time, Amount, Class, V1..V28)
    feature_cols = ["Time", "Amount", "Class"] + [f"V{i}" for i in range(1, 29)]
    df = df.dropDuplicates(feature_cols)

    # Add stable id for downstream (Silver)
    df = df.withColumn("transaction_id", F.monotonically_increasing_id())

    # Reorder: transaction_id first, then Time, V1–V28, Amount, Class, ingestion_ts, ingestion_source
    cols = ["transaction_id", "Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount", "Class", "ingestion_ts", "ingestion_source"]
    df = df.select([c for c in cols if c in df.columns])

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {full_db}")
    df.write.format("delta").mode("overwrite").saveAsTable(silver_full)
    return df.count()
