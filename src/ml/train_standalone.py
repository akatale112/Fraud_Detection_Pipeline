"""
Train the fraud model without using Spark (avoids spark.mlflow.modelRegistryUri).
Reads training data from a CSV or Parquet path. Run this when the notebook fails
due to CONFIG_NOT_AVAILABLE on Serverless/free tier.

Usage:
  python -m src.ml.train_standalone --data /path/to/silver.parquet --config config/config_dev.yaml
  # or
  python -m src.ml.train_standalone --data /path/to/silver.csv --config config/config_dev.yaml

To get the data: In Databricks Catalog, open silver_transactions → Export → download
or use a one-off Spark job to write: spark.table("workspace.fraud.silver_transactions").write.mode("overwrite").parquet("/Volumes/.../export/silver.parquet")
"""
import argparse
import json
import math
import os
from typing import Dict, Any

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from src.ingestion.batch_ingest import load_config
from src.features.fraud_features import FEATURE_COLUMNS


def _add_derived_features(pdf: pd.DataFrame) -> pd.DataFrame:
    if "Amount" in pdf.columns:
        pdf = pdf.copy()
        pdf["log_amount"] = (pdf["Amount"] + 1).apply(math.log)
    if "Time" in pdf.columns:
        pdf["time_hour"] = (pdf["Time"] % 86400) / 3600.0
    return pdf


def run_training_standalone(
    data_path: str,
    config_path: str,
    experiment_name: str = "fraud_detection",
) -> Dict[str, Any]:
    cfg = load_config(config_path)
    inference_cfg = cfg.get("real_time_inference", {})
    storage_cfg = cfg.get("storage", {})
    model_name = inference_cfg.get("model_name", "fraud_detection_model")

    if data_path.lower().endswith(".csv"):
        pdf = pd.read_csv(data_path)
    else:
        pdf = pd.read_parquet(data_path)

    pdf = _add_derived_features(pdf)
    feature_cols = [c for c in FEATURE_COLUMNS if c in pdf.columns]
    if "Class" not in pdf.columns:
        raise ValueError("Data must contain 'Class' column")
    if not feature_cols:
        raise ValueError("No feature columns found")

    pdf = pdf[feature_cols + ["Class"]].dropna()
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

    mlflow.set_tracking_uri("file:/tmp/mlflow")
    mlflow.set_experiment(experiment_name)
    run_id = None
    with mlflow.start_run() as run:
        run_id = run.info.run_id
        mlflow.log_params({"model_type": "LogisticRegression", "feature_cols": ",".join(feature_cols), "random_state": 42, "test_size": 0.2})
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(pipe, "model")

    base_path = storage_cfg.get("base_path", "/tmp").replace("dbfs:", "").strip()
    model_dir = (base_path.rstrip("/") + "/models") if base_path.startswith("/Volumes/") else "/tmp/fraud_models"
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "fraud_model.pkl")
    meta_path = os.path.join(model_dir, "feature_cols.json")
    joblib.dump(pipe, model_path)
    with open(meta_path, "w") as f:
        json.dump({"feature_cols": feature_cols}, f)

    return {"metrics": metrics, "model_name": model_name, "run_id": run_id, "model_path": model_path, "feature_cols_path": meta_path}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to silver data (CSV or Parquet)")
    parser.add_argument("--config", default="config/config_dev.yaml", help="Config YAML path")
    parser.add_argument("--experiment", default="fraud_detection", help="MLflow experiment name")
    args = parser.parse_args()
    result = run_training_standalone(args.data, args.config, args.experiment)
    print("Metrics:", result["metrics"])
    print("Model saved to:", result["model_path"])


if __name__ == "__main__":
    main()
