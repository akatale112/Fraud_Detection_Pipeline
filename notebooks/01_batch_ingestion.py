# Databricks notebook source

from src.ingestion.batch_ingest import run_batch_ingestion

config_path = "config/config_dev.yaml"
row_count = run_batch_ingestion(spark, config_path)
print(f"Ingested {row_count} rows into Bronze.")

