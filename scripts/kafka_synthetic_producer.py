#!/usr/bin/env python3
"""
Kafka Synthetic Transaction Producer for Fraud Detection Pipeline

Generates synthetic transaction data (Kaggle Credit Card Fraud–like schema),
injects fraud cases at a configurable rate, and streams records to Kafka
for real-time ingestion and inference testing.

Schema: Time, V1–V28, Amount, Class (0=normal, 1=fraud)
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime

# Optional: use numpy for faster/better distributions; fallback to random
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    import random

try:
    from confluent_kafka import Producer
except ImportError:
    print("Install confluent_kafka: pip install confluent-kafka", file=sys.stderr)
    sys.exit(1)


# --- Config (override via env or CLI) ---
DEFAULT_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DEFAULT_TOPIC = os.environ.get("KAFKA_TOPIC", "transactions")
DEFAULT_FRAUD_RATE = float(os.environ.get("FRAUD_RATE", "0.005"))  # 0.5% fraud
DEFAULT_RATE_PER_SEC = float(os.environ.get("RATE_PER_SEC", "10"))
DEFAULT_DURATION_SEC = int(os.environ.get("DURATION_SEC", "60"))  # 0 = run forever


def _random_float(low: float, high: float):
    if HAS_NUMPY:
        return float(np.random.uniform(low, high))
    return random.uniform(low, high)


def _random_normal(mean: float, std: float):
    if HAS_NUMPY:
        return float(np.random.normal(mean, std))
    # Box-Muller approximation using random
    u1, u2 = random.random(), random.random()
    import math
    z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
    return mean + std * z


def generate_one_transaction(
    fraud_rate: float,
    base_time_sec: int,
    transaction_id: str,
) -> dict:
    """
    Generate a single transaction (Kaggle-like).
    Fraud records get slightly different V1–V28 and Amount distributions
    so the model has a signal to learn.
    """
    is_fraud = _random_float(0, 1) < fraud_rate

    # Time: seconds elapsed (we use base_time_sec + small delta for variety)
    t = base_time_sec + int(_random_float(0, 3600))

    # V1–V28: PCA-like features. Fraud tends to have more extreme values in a few dimensions.
    features = {}
    for i in range(1, 29):
        if is_fraud:
            # Fraud: slightly higher variance and shifted mean in some dimensions
            mean = _random_float(-1, 1) if i % 5 == 0 else 0
            std = _random_float(1.5, 3.0)
        else:
            mean = 0
            std = _random_float(0.5, 1.5)
        features[f"V{i}"] = round(_random_normal(mean, std), 6)

    # Amount: fraud often has different distribution (e.g., higher or bimodal)
    if is_fraud:
        amount = _random_float(50, 2500) if _random_float(0, 1) < 0.6 else _random_float(1, 50)
    else:
        amount = round(_random_float(1, 500), 2)
    amount = max(0.01, amount)

    record = {
        "transaction_id": transaction_id,
        "Time": t,
        **features,
        "Amount": round(amount, 2),
        "Class": 1 if is_fraud else 0,
    }
    return record


def delivery_callback(err, msg):
    if err:
        print(f"Delivery failed: {err}", file=sys.stderr)
    # Uncomment for verbose logging:
    # else:
    #     print(f"Produced to {msg.topic()} partition {msg.partition()} offset {msg.offset()}")


def run_producer(
    bootstrap_servers: str,
    topic: str,
    fraud_rate: float,
    rate_per_sec: float,
    duration_sec: int,
):
    conf = {"bootstrap.servers": bootstrap_servers}
    producer = Producer(conf)
    base_time = int(time.time()) - 86400  # start from 1 day ago

    start = time.time()
    count = 0
    fraud_count = 0

    try:
        while True:
            elapsed = time.time() - start
            if duration_sec > 0 and elapsed >= duration_sec:
                break

            # Send ~rate_per_sec messages per second (burst then sleep 1s)
            n = max(1, int(rate_per_sec))
            for _ in range(n):
                tx_id = str(uuid.uuid4())
                record = generate_one_transaction(fraud_rate, base_time, tx_id)
                if record["Class"] == 1:
                    fraud_count += 1
                count += 1
                payload = json.dumps(record).encode("utf-8")
                producer.produce(topic, value=payload, key=tx_id.encode("utf-8"), callback=delivery_callback)
                base_time += int(_random_float(1, 30))  # advance time

            producer.poll(0)
            time.sleep(1.0)

    except KeyboardInterrupt:
        pass
    finally:
        producer.flush()

    print(f"Produced {count} records ({fraud_count} fraud, {count - fraud_count} normal) in {time.time() - start:.1f}s")
    return count


def main():
    parser = argparse.ArgumentParser(description="Produce synthetic fraud/non-fraud transactions to Kafka")
    parser.add_argument("--bootstrap-servers", default=DEFAULT_BOOTSTRAP, help="Kafka bootstrap servers")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help="Kafka topic name")
    parser.add_argument("--fraud-rate", type=float, default=DEFAULT_FRAUD_RATE, help="Fraction of transactions that are fraud (0–1)")
    parser.add_argument("--rate", type=float, default=DEFAULT_RATE_PER_SEC, help="Messages per second (approx)")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION_SEC, help="Run duration in seconds (0 = forever)")
    args = parser.parse_args()

    if not 0 <= args.fraud_rate <= 1:
        print("--fraud-rate must be between 0 and 1", file=sys.stderr)
        sys.exit(1)

    print(f"Starting producer: topic={args.topic} fraud_rate={args.fraud_rate} rate={args.rate}/s duration={args.duration}s")
    run_producer(
        args.bootstrap_servers,
        args.topic,
        args.fraud_rate,
        args.rate,
        args.duration,
    )


if __name__ == "__main__":
    main()
