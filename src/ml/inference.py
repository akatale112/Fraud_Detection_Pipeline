"""
Batch inference: score Silver transactions with the trained model and write to gold_transaction_scores.
Supports the standalone model (joblib at storage.base_path/models/fraud_model.pkl).

Real-time: Use Databricks Model Serving with the registered model; see docs/MODEL_SERVING.md
and REALTIME_INPUT_SCHEMA below for request shape.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional

import joblib
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructType,
    TimestampType,
)

from src.ingestion.batch_ingest import load_config
from src.features.fraud_features import add_fraud_features

# Schema for real-time inference requests (single or batch).
# Match Kafka/synthetic producer: Time, V1–V28, Amount; optional Class for validation.
REALTIME_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "Time": {"type": "number"},
        "Amount": {"type": "number"},
        "Class": {"type": "integer", "description": "Optional label (0/1) for validation"},
    },
    "required": ["Time", "Amount"],
}
for i in range(1, 29):
    REALTIME_INPUT_SCHEMA["properties"][f"V{i}"] = {"type": "number"}
    if i == 1:
        REALTIME_INPUT_SCHEMA["required"].append("V1")
# V2..V28 typically required for model; for brevity we require Time, Amount and expect V1–V28
for i in range(2, 29):
    REALTIME_INPUT_SCHEMA["required"].append(f"V{i}")


def _model_paths_from_config(cfg: dict) -> tuple:
    storage = cfg.get("storage", {})
    base = (storage.get("base_path") or "").strip().replace("dbfs:", "")
    if not base:
        raise ValueError("storage.base_path is not set")
    model_dir = base.rstrip("/") + "/models"
    return (model_dir + "/fraud_model.pkl", model_dir + "/feature_cols.json")


def run_batch_inference(
    spark: SparkSession,
    config_path: str,
    model_version: Optional[str] = None,
    mode: str = "overwrite",
) -> Dict[str, Any]:
    """
    Read silver_transactions, apply the saved model, write scores to gold_transaction_scores.

    Args:
        spark: Active SparkSession.
        config_path: Path to config YAML.
        model_version: Label for this run (e.g. "standalone_v1"). Default "standalone".
        mode: Write mode for gold_transaction_scores: "overwrite" or "append".

    Returns:
        Dict with keys: rows_scored, gold_table, model_path, model_version.
    """
    cfg = load_config(config_path)
    databricks_cfg = cfg.get("databricks", {})
    tables_cfg = cfg.get("tables", {})
    catalog = databricks_cfg.get("catalog", "")
    schema = databricks_cfg.get("schema")
    if not schema:
        raise ValueError("databricks.schema is not set in config")

    silver_table = tables_cfg.get("silver_transactions", "silver_transactions")
    gold_scores_table = tables_cfg.get("gold_transaction_scores", "gold_transaction_scores")
    full_db = f"{catalog}.{schema}" if catalog else schema
    silver_full = f"{full_db}.{silver_table}"
    gold_full = f"{full_db}.{gold_scores_table}"

    model_path, meta_path = _model_paths_from_config(cfg)
    with open(meta_path, "r") as f:
        meta = json.load(f)
    feature_cols: List[str] = meta.get("feature_cols") or []
    if not feature_cols:
        raise ValueError(f"No feature_cols in {meta_path}")

    pipe = joblib.load(model_path)
    version = model_version or "standalone"
    scored_at = datetime.now(timezone.utc)

    # Read Silver and add derived features
    df: DataFrame = spark.table(silver_full)
    df = add_fraud_features(df)

    # Select keys and features; drop rows with null in any feature
    select_cols = ["transaction_id"] + [c for c in feature_cols if c in df.columns]
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Silver table missing feature columns: {missing}")
    df = df.select(select_cols).dropna()

    pdf = df.toPandas()
    if pdf.empty:
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {full_db}")
        empty_schema = (
            StructType()
            .add("transaction_id", LongType())
            .add("score", DoubleType())
            .add("prediction", IntegerType())
            .add("model_version", StringType())
            .add("scored_at", TimestampType())
        )
        empty = spark.createDataFrame([], empty_schema)
        empty.write.format("delta").mode(mode).saveAsTable(gold_full)
        return {
            "rows_scored": 0,
            "gold_table": gold_full,
            "model_path": model_path,
            "model_version": version,
        }

    X = pdf[feature_cols]
    scores = pipe.predict_proba(X)[:, 1]
    preds = pipe.predict(X)

    result_pdf = pdf[["transaction_id"]].copy()
    result_pdf["score"] = scores
    result_pdf["prediction"] = preds.astype(int)
    result_pdf["model_version"] = version
    result_pdf["scored_at"] = scored_at

    result_schema = (
        StructType()
        .add("transaction_id", LongType())
        .add("score", DoubleType())
        .add("prediction", IntegerType())
        .add("model_version", StringType())
        .add("scored_at", TimestampType())
    )
    result_df = spark.createDataFrame(result_pdf, schema=result_schema)

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {full_db}")
    result_df.write.format("delta").mode(mode).saveAsTable(gold_full)

    return {
        "rows_scored": len(result_pdf),
        "gold_table": gold_full,
        "model_path": model_path,
        "model_version": version,
    }
