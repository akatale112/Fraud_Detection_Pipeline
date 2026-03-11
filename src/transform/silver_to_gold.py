"""
Silver → Gold: build dashboard-ready aggregates (daily fraud summary).
Reads from silver_transactions, writes to gold_fraud_daily_summary (managed table).
"""
from typing import Optional

from pyspark.sql import SparkSession, DataFrame, functions as F

from src.ingestion.batch_ingest import load_config


def run_silver_to_gold(
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

    silver_table = tables_cfg.get("silver_transactions", "silver_transactions")
    gold_summary_table = tables_cfg.get("gold_fraud_daily_summary", "gold_fraud_daily_summary")
    full_db = f"{catalog}.{schema}" if catalog else schema
    silver_full = f"{full_db}.{silver_table}"
    gold_summary_full = f"{full_db}.{gold_summary_table}"

    df: DataFrame = spark.table(silver_full)

    # Use ingestion date for daily grouping (or fallback to time bucket from Time if no ts)
    if "ingestion_ts" in df.columns:
        df = df.withColumn("report_date", F.to_date(F.col("ingestion_ts")))
    else:
        # Kaggle Time = seconds since first txn; treat 86400 sec = 1 day
        df = df.withColumn("report_date", F.to_date(F.from_unixtime(F.floor(F.col("Time") / 86400) * 86400)))

    summary = (
        df.groupBy("report_date")
        .agg(
            F.count("*").alias("total_txn"),
            F.sum(F.when(F.col("Class") == 1, 1).otherwise(0)).alias("fraud_count"),
            F.sum("Amount").alias("total_amount"),
            F.sum(F.when(F.col("Class") == 1, F.col("Amount")).otherwise(0)).alias("fraud_amount"),
        )
        .withColumn(
            "fraud_rate",
            F.when(F.col("total_txn") > 0, F.col("fraud_count") / F.col("total_txn")).otherwise(0),
        )
        .orderBy("report_date")
    )

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {full_db}")
    summary.write.format("delta").mode("overwrite").saveAsTable(gold_summary_full)
    return summary.count()

