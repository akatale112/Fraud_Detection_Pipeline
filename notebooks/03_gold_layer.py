# Databricks notebook source

import os
os.chdir("/Workspace/Users/akatale@umd.edu/Fraud_Detection_Pipeline")

from src.transform.silver_to_gold import run_silver_to_gold

config_path = "config/config_dev.yaml"
row_count = run_silver_to_gold(spark, config_path)
print(f"Gold layer updated: {row_count} row(s) in gold_fraud_daily_summary.")
