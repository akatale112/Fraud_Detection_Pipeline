# Databricks notebook source

import os
os.chdir("/Workspace/Users/akatale@umd.edu/Fraud_Detection_Pipeline")

from src.transform.bronze_to_silver import run_bronze_to_silver

config_path = "config/config_dev.yaml"
row_count = run_bronze_to_silver(spark, config_path)
print(f"Silver layer updated: {row_count} rows in silver_transactions.")
