# Financial Fraud Detection Data Pipeline

This repository contains an end-to-end **financial fraud detection data pipeline** built for **Databricks**, using:

- PySpark + Delta Lake
- Medallion architecture (Bronze → Silver → Gold)
- Kafka + Structured Streaming (for real-time ingestion)
- MLflow (for model tracking and serving)
- Databricks Workflows and optionally Delta Live Tables

> You approved the implementation plan in `IMPLEMENTATION_PLAN.md`. Implementation now starts with **Phase 0: Setup & Environment** in this folder.

---

## Phase 0 – Setup & Environment

The goal of Phase 0 is to get your environment ready **without** building pipeline logic yet.

### 1. Local project setup (this repo)

1. Ensure you are in the project directory:

   ```bash
   cd /Users/aditi0810/Desktop/Fraud_Detection_Pipeline
   ```

2. (Optional but recommended) Create a virtual environment for local tools and scripts:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies for the Kafka synthetic producer (used later for streaming tests and real-time inference):

   ```bash
   pip install -r scripts/requirements_producer.txt
   ```

4. Verify the producer script is available:

   ```bash
   python scripts/kafka_synthetic_producer.py --help
   ```

   If you see the help text, Phase 0 local script setup is OK.

### 2. Databricks workspace setup (high level)

In your Databricks workspace:

- Create (or identify) a **cluster** with:
  - Runtime: Spark 3.x with Delta Lake
  - Python 3.10+ (or closest available)
- Create a **catalog/schema** (or database) for this project (e.g., `fraud`).
- Configure **DBFS or mounts** where you will store:
  - Raw/batch Kaggle data (landing zone)
  - Bronze/Silver/Gold Delta tables (e.g., under `dbfs:/mnt/fraud_project/`).

### 3. Kafka setup (for streaming)

You will need a Kafka cluster and a topic, for example:

- Kafka brokers (e.g., `localhost:9092` for local, or Confluent Cloud brokers).
- A topic, e.g., `transactions`.

Steps (conceptual):

1. Create a Kafka topic:

   ```bash
   kafka-topics --create \
     --bootstrap-server <your-broker> \
     --topic transactions \
     --partitions 3 \
     --replication-factor 1
   ```

2. Note the **bootstrap servers** and **topic name** – you will put these into the config files in `config/`.

3. Later phases will:
   - Run `scripts/kafka_synthetic_producer.py` to send synthetic transactions (including fraud) to this topic.
   - Configure a Databricks Structured Streaming job to read from this topic.

### 4. Kaggle dataset in cloud/DBFS

For batch ingestion:

1. Download the **Kaggle Credit Card Fraud** dataset (CSV) to your machine.
2. Upload it to DBFS or cloud storage, e.g.:

   ```bash
   databricks fs cp creditcard.csv dbfs:/mnt/fraud_project/raw/creditcard.csv
   ```

   (Adjust path and CLI usage based on your Databricks setup.)

3. Record the final path (e.g., `dbfs:/mnt/fraud_project/raw/creditcard.csv`) – we will reference this in `config/config_dev.yaml` in later phases.

---

## Testing Phase 0

After completing Phase 0, you should be able to:

- Run:

  ```bash
  cd /Users/aditi0810/Desktop/Fraud_Detection_Pipeline
  python scripts/kafka_synthetic_producer.py --help
  ```

  and see the usage message.

- Confirm:
  - Your Databricks cluster is available.
  - A Kafka topic exists for `transactions`.
  - The Kaggle dataset is uploaded to a reachable DBFS/cloud path.

No Spark jobs, Delta tables, or ML components are created yet; those start from **Phase 1** onward.

---

For detailed design and later phases, see `IMPLEMENTATION_PLAN.md`.

