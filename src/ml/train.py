"""
Train a binary fraud classifier on Silver data.
Uses file-based MLflow tracking to avoid spark.mlflow.modelRegistryUri; also saves
model to a path (joblib) so Phase 5 inference can load by path without the registry.
"""
import json
import os
from typing import Optional, Dict, Any

import joblib
import mlflow
import mlflow.sklearn
from pyspark.sql import SparkSession
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

from src.ingestion.batch_ingest import load_config
from src.features.fraud_features import add_fraud_features, FEATURE_COLUMNS


def run_training(
    spark: SparkSession,
    config_path: str,
    experiment_name: Optional[str] = "fraud_detection",
    env: Optional[str] = "dev",
) -> Dict[str, Any]:
    cfg = load_config(config_path)
    databricks_cfg = cfg.get("databricks", {})
    tables_cfg = cfg.get("tables", {})
    inference_cfg = cfg.get("real_time_inference", {})

    catalog = databricks_cfg.get("catalog", "")
    schema = databricks_cfg.get("schema")
    if not schema:
        raise ValueError("databricks.schema is not set in config")

    silver_table = tables_cfg.get("silver_transactions", "silver_transactions")
    model_name = inference_cfg.get("model_name", "fraud_detection_model")
    full_db = f"{catalog}.{schema}" if catalog else schema
    silver_full = f"{full_db}.{silver_table}"

    df = spark.table(silver_full)
    df = add_fraud_features(df)

    # Use only columns that exist
    feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
    if "Class" not in df.columns:
        raise ValueError("Silver table must contain 'Class' column")
    if not feature_cols:
        raise ValueError("No feature columns found")

    pdf = df.select(feature_cols + ["Class"]).dropna().toPandas()
    X = pdf[feature_cols]
    y = pdf["Class"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=500, random_state=42, class_weight="balanced")),
    ])
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    y_proba = pipe.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_proba) if y_test.nunique() > 1 else 0.0,
    }

    # File-based MLflow only (avoids spark.mlflow.modelRegistryUri on Serverless/free tier)
    mlflow.set_tracking_uri("file:/tmp/mlflow")
    if experiment_name:
        mlflow.set_experiment(experiment_name)
    run_id = None
    with mlflow.start_run() as run:
        run_id = run.info.run_id
        mlflow.log_params({
            "model_type": "LogisticRegression",
            "feature_cols": ",".join(feature_cols),
            "random_state": 42,
            "test_size": 0.2,
        })
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(pipe, "model")

    # Save model and feature list to path so Phase 5 can load without Model Registry
    storage_cfg = cfg.get("storage", {})
    base_path = storage_cfg.get("base_path", "/tmp").replace("dbfs:", "").strip()
    if base_path.startswith("/Volumes/"):
        model_dir = base_path.rstrip("/") + "/models"
    else:
        model_dir = "/tmp/fraud_models"
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "fraud_model.pkl")
    meta_path = os.path.join(model_dir, "feature_cols.json")
    joblib.dump(pipe, model_path)
    with open(meta_path, "w") as f:
        json.dump({"feature_cols": feature_cols}, f)

    return {
        "metrics": metrics,
        "model_name": model_name,
        "run_id": run_id,
        "model_path": model_path,
        "feature_cols_path": meta_path,
    }
