"""
Streaming ingestion from Kafka into Bronze.
Reads JSON messages from a Kafka topic, parses to Kaggle-like schema,
adds ingestion_ts and ingestion_source, and appends to bronze_transactions.

Requires Kafka to be reachable from the cluster (bootstrap_servers in config).
Use scripts/kafka_synthetic_producer.py to produce test data.
"""
from typing import Optional

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DoubleType,
)

from src.ingestion.batch_ingest import load_config


def _kafka_value_schema() -> StructType:
    """Schema of JSON value produced by kafka_synthetic_producer (transaction_id, Time, V1–V28, Amount, Class)."""
    fields = [
        StructField("transaction_id", StringType(), True),
        StructField("Time", IntegerType(), True),
    ]
    for i in range(1, 29):
        fields.append(StructField(f"V{i}", DoubleType(), True))
    fields.append(StructField("Amount", DoubleType(), True))
    fields.append(StructField("Class", IntegerType(), True))
    return StructType(fields)


def run_stream_ingestion(
    spark: SparkSession,
    config_path: str,
    checkpoint_base: Optional[str] = None,
):
    """
    Start a streaming query: Kafka topic -> parse JSON -> append to Bronze.

    Uses config: kafka.bootstrap_servers, kafka.topic_transactions,
    databricks.catalog/schema, tables.bronze_transactions, storage.base_path.

    checkpoint_base: directory for Spark checkpoint (default: storage.base_path/checkpoints/kafka_bronze).
    Returns the active StreamingQuery; call .awaitTermination() to block.
    """
    cfg = load_config(config_path)
    kafka_cfg = cfg.get("kafka", {})
    databricks_cfg = cfg.get("databricks", {})
    tables_cfg = cfg.get("tables", {})
    storage_cfg = cfg.get("storage", {})

    bootstrap = kafka_cfg.get("bootstrap_servers") or "localhost:9092"
    topic = kafka_cfg.get("topic_transactions") or "transactions"
    catalog = databricks_cfg.get("catalog", "")
    schema = databricks_cfg.get("schema")
    if not schema:
        raise ValueError("databricks.schema is not set in config")
    bronze_table = tables_cfg.get("bronze_transactions", "bronze_transactions")
    full_db = f"{catalog}.{schema}" if catalog else schema
    table_name = f"{full_db}.{bronze_table}"

    base_path = (storage_cfg.get("base_path") or "").strip().replace("dbfs:", "")
    if not base_path:
        raise ValueError("storage.base_path is not set")
    checkpoint = checkpoint_base or (base_path.rstrip("/") + "/checkpoints/kafka_bronze")

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {full_db}")

    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap)
        .option("subscribe", topic)
        .option("startingOffsets", "latest")
        .load()
    )

    value_schema = _kafka_value_schema()
    parsed = (
        raw.select(F.from_json(F.col("value").cast("string"), value_schema).alias("data"))
        .select("data.*")
        .withColumn("ingestion_ts", F.current_timestamp())
        .withColumn("ingestion_source", F.lit("kafka"))
    )

    # Select column order: transaction_id (from Kafka), Time, V1–V28, Amount, Class, ingestion_ts, ingestion_source
    cols = ["transaction_id", "Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount", "Class", "ingestion_ts", "ingestion_source"]
    parsed = parsed.select([c for c in cols if c in parsed.columns])

    query = (
        parsed.writeStream
        .format("delta")
        .outputMode("append")
        .option("checkpointLocation", checkpoint)
        .option("mergeSchema", "true")
        .toTable(table_name)
    )
    return query


