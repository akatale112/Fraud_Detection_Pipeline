# Databricks notebook source
# MAGIC %md
# MAGIC ## Export Silver table for Phase 4 (standalone training)
# MAGIC Run this on a **classic cluster** (not Serverless) to export `silver_transactions` to a file.
# MAGIC Then set `ml.training_data_path` in config to this path and run `04_ml_training` (standalone path).
# MAGIC On Serverless, export via **SQL Editor** (query table → Download CSV) and upload to your Volume instead.

# Databricks notebook source

import os
os.chdir("/Workspace/Users/akatale@umd.edu/Fraud_Detection_Pipeline")

from src.ingestion.batch_ingest import load_config

cfg = load_config("config/config_dev.yaml")
storage = cfg.get("storage", {})
base = (storage.get("base_path") or "/tmp").replace("dbfs:", "").strip()
export_dir = base.rstrip("/") + "/export"

catalog = cfg.get("databricks", {}).get("catalog", "")
schema = cfg.get("databricks", {}).get("schema", "fraud")
silver_table = cfg.get("tables", {}).get("silver_transactions", "silver_transactions")
full_name = f"{catalog}.{schema}.{silver_table}" if catalog else f"{schema}.{silver_table}"

# Write as Parquet (single partition) so standalone trainer can read without Spark
df = spark.table(full_name)
parquet_path = export_dir.rstrip("/") + "/silver"
df.coalesce(1).write.mode("overwrite").parquet(parquet_path)

# Path is a directory; pandas read_parquet accepts dirs. Use the dir path.
print(f"Exported to {parquet_path}")
print("In config set: ml:  training_data_path:", parquet_path)
