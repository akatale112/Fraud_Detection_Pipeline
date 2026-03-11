from typing import Optional

import yaml
from pyspark.sql import SparkSession, DataFrame, functions as F


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        cfg = yaml.safe_load(f) or {}

    def resolve(obj, config: dict):
        if isinstance(obj, str):
            s = obj
            while "${" in s and "}" in s:
                start = s.index("${") + 2
                end = s.index("}", start)
                key = s[start:end].strip()
                parts = key.split(".")
                val = config
                for p in parts:
                    val = val.get(p) if isinstance(val, dict) else None
                if val is None or (isinstance(val, str) and val.startswith("${")):
                    break
                s = s[: start - 2] + str(val) + s[end + 1 :]
            return s
        if isinstance(obj, dict):
            return {k: resolve(v, config) for k, v in obj.items()}
        if isinstance(obj, list):
            return [resolve(v, config) for v in obj]
        return obj

    return resolve(cfg, cfg)


def _spark_path(path: str) -> str:
    """Ensure path has a scheme so Spark accepts it (e.g. dbfs:/Volumes/...)."""
    if not path or "://" in path:
        return path
    path = path.strip()
    if path.startswith("/Volumes/") or path.startswith("/"):
        return "dbfs:" + path
    return path


def run_batch_ingestion(
    spark: SparkSession,
    config_path: str,
    env: Optional[str] = "dev",
) -> int:
    cfg = load_config(config_path)

    databricks_cfg = cfg.get("databricks", {})
    storage_cfg = cfg.get("storage", {})
    tables_cfg = cfg.get("tables", {})
    data_sources_cfg = cfg.get("data_sources", {})

    kaggle_path = data_sources_cfg.get("kaggle_credit_card_csv")
    if not kaggle_path:
        raise ValueError("kaggle_credit_card_csv is not set in config")
    kaggle_path = _spark_path(kaggle_path)

    catalog = databricks_cfg.get("catalog", "")
    schema = databricks_cfg.get("schema")
    if not schema:
        raise ValueError("databricks.schema is not set in config")

    bronze_table_name = tables_cfg.get("bronze_transactions", "bronze_transactions")
    full_db = f"{catalog}.{schema}" if catalog else schema
    full_table_name = f"{full_db}.{bronze_table_name}"

    df: DataFrame = (
        spark.read.option("header", "true")
        .option("inferSchema", "true")
        .csv(kaggle_path)
        .withColumn("ingestion_ts", F.current_timestamp())
        .withColumn("ingestion_source", F.lit("batch"))
    )

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {full_db}")
    # Use managed table (no LOCATION) to avoid UC path/scheme restrictions on free edition
    df.write.format("delta").mode("append").saveAsTable(full_table_name)

    return df.count()


def main():
    spark = SparkSession.builder.appName("BatchIngestionKaggleFraud").getOrCreate()
    config_path = "config/config_dev.yaml"
    count = run_batch_ingestion(spark, config_path)
    print(f"Ingested {count} rows into Bronze")
    spark.stop()


if __name__ == "__main__":
    main()

