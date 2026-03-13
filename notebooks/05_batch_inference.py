# Databricks notebook source
# MAGIC %md
# MAGIC ## Phase 5: Batch Inference
# MAGIC Scores `silver_transactions` with the trained model and writes results to `gold_transaction_scores` (transaction_id, score, prediction, model_version, scored_at).
# MAGIC Requires the model at `storage.base_path/models/fraud_model.pkl` and `feature_cols.json` (from Phase 4).

# Databricks notebook source

import os
os.chdir("/Workspace/Users/akatale@umd.edu/Fraud_Detection_Pipeline")

from src.ml.inference import run_batch_inference

config_path = "config/config_dev.yaml"
result = run_batch_inference(spark, config_path, mode="overwrite")
print(f"Batch inference complete: {result['rows_scored']} row(s) written to {result['gold_table']}.")
print(f"Model: {result['model_path']} (version: {result['model_version']})")
