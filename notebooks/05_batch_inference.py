import os
os.chdir("/Workspace/Users/akatale@umd.edu/Fraud_Detection_Pipeline")

from src.ml.inference import run_batch_inference

config_path = "config/config_dev.yaml"
result = run_batch_inference(spark, config_path, mode="overwrite")
print(f"Batch inference complete: {result['rows_scored']} row(s) written to {result['gold_table']}.")
print(f"Model: {result['model_path']} (version: {result['model_version']})")
