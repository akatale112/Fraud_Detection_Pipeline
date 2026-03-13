# Databricks notebook source
# MAGIC %md
# MAGIC ## Phase 6: Streaming Ingestion from Kafka
# MAGIC Reads JSON from the Kafka topic (config: `kafka.bootstrap_servers`, `kafka.topic_transactions`), parses to Kaggle-like schema, and **appends** to `bronze_transactions` with `ingestion_source = 'kafka'`.
# MAGIC Run the synthetic producer (`scripts/kafka_synthetic_producer.py`) elsewhere to send messages. This cell starts the stream and blocks until stopped.

# Databricks notebook source
import os
os.chdir("/Workspace/Users/akatale@umd.edu/Fraud_Detection_Pipeline")

from src.ingestion.stream_ingest import run_stream_ingestion

config_path = "config/config_dev.yaml"
query = run_stream_ingestion(spark, config_path)
print("Stream started (AvailableNow: process all available Kafka messages then stop). Waiting for completion...")
query.awaitTermination()
print("Stream finished. New Kafka data has been appended to Bronze.")
