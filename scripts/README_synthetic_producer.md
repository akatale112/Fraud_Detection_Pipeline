# Synthetic Transaction Producer for Kafka

## Purpose

`kafka_synthetic_producer.py` generates **synthetic transaction data** in the same schema as the Kaggle Credit Card Fraud dataset, **injects fraud** (Class=1) at a configurable rate, and **streams records to Kafka**. This feeds your streaming pipeline and real-time inference (Model Serving) with a continuous flow of transactions.

## Schema (per message, JSON)

| Field | Type | Description |
|-------|------|-------------|
| `transaction_id` | string | UUID per transaction |
| `Time` | int | Seconds (elapsed-style) |
| `V1`–`V28` | float | Synthetic PCA-like features (fraud has different distribution) |
| `Amount` | float | Transaction amount |
| `Class` | 0 or 1 | 0 = normal, 1 = fraud |

## Prerequisites

- Python 3.8+
- Kafka cluster (local or Confluent Cloud, etc.) with a topic created
- Optional: `numpy` for better random distributions (`pip install numpy`)

## Install

```bash
pip install confluent-kafka
# optional
pip install numpy
```

## Usage

**Default (10 msg/s, 0.5% fraud, 60 seconds):**

```bash
python kafka_synthetic_producer.py
```

**Custom options:**

```bash
python kafka_synthetic_producer.py \
  --bootstrap-servers your-broker:9092 \
  --topic transactions \
  --fraud-rate 0.01 \
  --rate 50 \
  --duration 0
```

| Option | Default | Description |
|--------|---------|-------------|
| `--bootstrap-servers` | `localhost:9092` or `KAFKA_BOOTSTRAP_SERVERS` | Kafka brokers |
| `--topic` | `transactions` or `KAFKA_TOPIC` | Topic name |
| `--fraud-rate` | `0.005` (0.5%) or `FRAUD_RATE` | Fraction of transactions that are fraud (0–1) |
| `--rate` | `10` or `RATE_PER_SEC` | Approximate messages per second |
| `--duration` | `60` or `DURATION_SEC` | Run duration in seconds; `0` = run until Ctrl+C |

**Environment variables:** `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC`, `FRAUD_RATE`, `RATE_PER_SEC`, `DURATION_SEC` override defaults.

## Flow (Step 7 – Real-time inference)

1. Run this script (on your laptop or a VM) to produce synthetic data to Kafka.
2. Your Databricks **streaming job** reads from Kafka → Bronze → Silver.
3. **Real-time inference**: each transaction (or micro-batch) is sent to **Databricks Model Serving**; the API returns a fraud score.
4. Optionally, scores are written back to a Gold table for dashboards.

This script is the **data source** for that stream; it does not call the model itself.
