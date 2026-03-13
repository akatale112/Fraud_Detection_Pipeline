# Phase 6: Streaming Ingestion and Real-Time Flow

## What’s implemented

- **Kafka → Bronze:** Structured Streaming job reads JSON from a Kafka topic, parses to Kaggle-like schema (transaction_id, Time, V1–V28, Amount, Class), adds `ingestion_ts` and `ingestion_source = 'kafka'`, and appends to **`bronze_transactions`** with schema merge so the table can have an optional `transaction_id` column from Kafka.
- **Notebook:** `notebooks/06_stream_ingestion_kafka.py` starts the stream and blocks until cancelled.
- **Producer:** `scripts/kafka_synthetic_producer.py` generates synthetic transactions (with configurable fraud rate) and publishes to Kafka.

## How to run

### 1. Kafka and config

- Have a Kafka cluster and topic (e.g. `transactions`). In **`config/config_dev.yaml`** set:
  - `kafka.bootstrap_servers` (e.g. `localhost:9092` or your broker).
  - `kafka.topic_transactions` (e.g. `transactions`).
- Your Databricks cluster must be able to reach the Kafka bootstrap servers (network/security groups and optional SASL/SSL in config for prod).

### 2. Start the streaming job in Databricks

- Open **`notebooks/06_stream_ingestion_kafka.py`**, set `os.chdir` to your repo path, run the cell.
- The stream runs until you cancel. Checkpoint is under **`storage.base_path/checkpoints/kafka_bronze`**.

### 3. Produce test data

- On a machine that can reach Kafka (and where the producer can run), install deps and run:
  ```bash
  pip install confluent-kafka numpy
  python scripts/kafka_synthetic_producer.py --bootstrap-servers <your-broker> --topic transactions --duration 60
  ```
- Messages will be consumed by the Databricks stream and appended to Bronze.

### 4. Process streamed data (Silver / Gold / scores)

- **Bronze → Silver → Gold:** Run **`02_silver_layer`** and **`03_gold_layer`** (manually or on a schedule) to process new Bronze rows (including Kafka-sourced ones). Existing logic deduplicates and adds `transaction_id` in Silver; Kafka-sourced rows get a new id in Silver like batch rows.
- **Scoring:** Run **`05_batch_inference`** to score the updated Silver table and write to **`gold_transaction_scores`**.

## Real-time scoring (optional)

- To score **each** Kafka message with low latency, use **Databricks Model Serving**: register the fraud model, create a serving endpoint, and call it from a Kafka consumer or a small service that reads from Kafka and posts to the endpoint. Request schema is in **`docs/MODEL_SERVING.md`** and **`src/ml/inference.REALTIME_INPUT_SCHEMA`**.
- You can write those scores back to **`gold_transaction_scores`** (e.g. via a small API that also writes to Delta) for dashboards.

## Summary

| Step              | What to run / use                                      |
|-------------------|--------------------------------------------------------|
| Stream Kafka→Bronze | `notebooks/06_stream_ingestion_kafka.py`              |
| Produce test data | `scripts/kafka_synthetic_producer.py`                 |
| Bronze→Silver→Gold | `02_silver_layer`, `03_gold_layer` (same as batch)    |
| Batch scoring     | `05_batch_inference` (after Silver is updated)        |
| Real-time scoring | Model Serving + consumer; see `docs/MODEL_SERVING.md` |
