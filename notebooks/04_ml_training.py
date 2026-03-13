# Databricks notebook source
# MAGIC %md
# MAGIC ## Phase 4: Feature Engineering & ML Training
# MAGIC Trains a binary fraud classifier from Silver data. Use **standalone** path on Serverless (set `ml.training_data_path` in config); use **Spark** path on classic clusters with `spark.mlflow.modelRegistryUri` set.

# Databricks notebook source

import os
import subprocess
import sys

os.chdir("/Workspace/Users/akatale@umd.edu/Fraud_Detection_Pipeline")

config_path = "config/config_dev.yaml"

from src.ingestion.batch_ingest import load_config
cfg = load_config(config_path)
training_data_path = (cfg.get("ml") or {}).get("training_data_path")

# ---- Path A: Standalone (no Spark) - use when ml.training_data_path is set (e.g. Serverless)
if training_data_path and os.path.exists(training_data_path):
    print("Using standalone training (data path set). No Spark used.")
    out = subprocess.run(
        [sys.executable, "-m", "src.ml.train_standalone", "--data", training_data_path, "--config", config_path],
        cwd=os.getcwd(), capture_output=False
    )
    if out.returncode != 0:
        raise RuntimeError("Standalone training failed. Check the output above.")
    print("Phase 4 complete. Model and feature_cols are under storage.base_path/models/")
else:
    # ---- Path B: Spark path (read from silver_transactions) - needs cluster with spark.mlflow.modelRegistryUri
    try:
        from src.ml.train import run_training
        result = run_training(spark, config_path)
        print("Training complete. Metrics:", result["metrics"])
        print("Model path:", result.get("model_path"), "| Model name:", result["model_name"])
    except Exception as e:
        err = str(e)
        if "modelRegistryUri" in err or "CONFIG_NOT_AVAILABLE" in err or "42K0" in err:
            print("Spark path failed (missing spark.mlflow.modelRegistryUri).")
            print("To use standalone: export silver_transactions (SQL Editor → Download CSV), upload to a path,")
            print("then in config add:  ml:  training_data_path: <path>  and re-run. See docs/MLFLOW_CLUSTER_FIX.md")
            raise
        else:
            raise
