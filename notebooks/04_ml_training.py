# Databricks notebook source

import os
os.chdir("/Workspace/Users/akatale@umd.edu/Fraud_Detection_Pipeline")

from src.ml.train import run_training

config_path = "config/config_dev.yaml"
result = run_training(spark, config_path)
print("Training complete. Metrics:", result["metrics"])
print("Registered model name:", result["model_name"])
