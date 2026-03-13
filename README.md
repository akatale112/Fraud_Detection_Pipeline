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

## Phase 2 – Silver Layer (Cleaning, DQ, Dedup)

After **Phase 1** has run (Bronze populated), run the Silver transformation:

1. In Databricks, open **`notebooks/02_silver_layer.py`**.
2. Set the working directory in the notebook to your project root (same as in `01_batch_ingestion`), e.g.  
   `os.chdir("/Workspace/Users/<your-email>/Fraud_Detection_Pipeline")`.
3. Attach the notebook to your cluster (e.g. Serverless) and run all cells.

This reads from `bronze_transactions`, applies validation (non-null key columns, `Amount > 0`, `Class` in 0/1), deduplicates, adds `transaction_id`, and writes to **`silver_transactions`** (managed table).

### Testing Phase 2

- After the notebook runs, in **Catalog** open your schema (e.g. `workspace.fraud`) and check table **`silver_transactions`**.
- Run:  
  `SELECT COUNT(*), COUNT(DISTINCT transaction_id) FROM workspace.fraud.silver_transactions;`  
  Row count and distinct `transaction_id` count should match (one id per row).
- Spot-check:  
  `SELECT * FROM workspace.fraud.silver_transactions LIMIT 10;`

---

## Phase 3 – Gold Layer (KPIs and Dashboard Tables)

After **Phase 2** (Silver populated), run the Gold aggregation:

1. In Databricks, open **`notebooks/03_gold_layer.py`**.
2. Set the working directory to your project root (same path as in Phase 1/2).
3. Attach the notebook to your cluster and run all cells.

This reads from `silver_transactions`, groups by **report_date** (from `ingestion_ts`), and writes **`gold_fraud_daily_summary`** with: `report_date`, `total_txn`, `fraud_count`, `total_amount`, `fraud_amount`, `fraud_rate`.

### Testing Phase 3

- In **Catalog** → your schema, open **`gold_fraud_daily_summary`** and use **Preview**, or run:

  ```sql
  SELECT * FROM workspace.fraud.gold_fraud_daily_summary ORDER BY report_date;
  ```

- In **SQL Editor** or **Dashboards**, you can build charts from this table (e.g. fraud rate over time, total amount by day). **`gold_transaction_scores`** is added in Phase 5 (ML inference).

---

## Phase 4 – Feature Engineering & ML Training

After **Phase 3** (Gold and Silver populated), run the training pipeline.

**Two ways to run (pick one):**

### Option A: Standalone (recommended on Serverless)

1. **Get Silver data as a file**
   - **Classic cluster:** Run **`notebooks/04a_export_silver_for_training.py`** once; it writes `silver_transactions` to Parquet under `storage.base_path/export/silver`.
   - **Serverless:** In **SQL Editor**, run `SELECT * FROM workspace.fraud.silver_transactions`, download as CSV, upload to your Volume (e.g. `.../export/silver_transactions.csv`).
2. In **`config/config_dev.yaml`** add (use the path you have):
   ```yaml
   ml:
     training_data_path: /Volumes/workspace/fraud/fraud_data/export/silver
   ```
   (Use the Parquet folder path from 04a, or the CSV file path from SQL export.)
3. Open **`notebooks/04_ml_training.py`**, set `os.chdir` to your project root, run all cells. It will use **standalone** training (no Spark); model and `feature_cols.json` are written to `storage.base_path/models/`.

### Option B: Spark path (classic cluster with MLflow config)

1. On your cluster, set Spark config: **`spark.mlflow.modelRegistryUri`** = **`databricks`** (Compute → cluster → Edit → Advanced options → Spark).
2. Open **`notebooks/04_ml_training.py`**, run all cells. It will read from `silver_transactions` and train using Spark; model is logged to MLflow and also saved under `storage.base_path/models/`.

**What Phase 4 does:** Adds fraud features (`log_amount`, `time_hour`), trains a **LogisticRegression** pipeline (StandardScaler + classifier, class_weight="balanced"), evaluates (accuracy, precision, recall, F1, ROC-AUC), logs to file-based MLflow, and saves the model as `fraud_model.pkl` and feature list as `feature_cols.json` for Phase 5.

### Testing Phase 4

- Check **`storage.base_path/models/`** (e.g. in Catalog → your Volume): you should see **`fraud_model.pkl`** and **`feature_cols.json`**.
- If you used the Spark path with Databricks MLflow, open **MLflow** → experiment **`fraud_detection`** and confirm a run with metrics.
- Install deps if needed: **`pip install -r requirements_ml.txt`** (for standalone or local runs).

---

## Phase 5 – Inference (Batch + Real-Time Preparation)

After **Phase 4** (model and `feature_cols.json` under `storage.base_path/models/`), you can score transactions and write results to Gold.

### Batch inference

1. Ensure **`silver_transactions`** exists and the model artifacts exist at **`storage.base_path/models/`** (`fraud_model.pkl`, `feature_cols.json`).
2. Open **`notebooks/05_batch_inference.py`**, set `os.chdir` to your repo path (e.g. `/Workspace/Users/<your-user>/Fraud_Detection_Pipeline`), then run all cells.
3. The job reads Silver, adds derived features, scores with the saved model, and writes to **`gold_transaction_scores`** with: `transaction_id`, `score`, `prediction`, `model_version`, `scored_at`.

**Testing:** Query the scores table, e.g. `SELECT * FROM workspace.fraud.gold_transaction_scores LIMIT 20;`

### Real-time inference (Model Serving)

To expose the model as an HTTP endpoint for low-latency scoring (e.g. for streaming or APIs), register the model in MLflow, create a **Databricks Model Serving** endpoint, and call it with the expected schema. See **`docs/MODEL_SERVING.md`** for step-by-step setup and the real-time request schema.

---

## Phase 6 – Streaming Ingestion (Kafka → Bronze)

Stream transaction events from Kafka into the same Bronze table (append with `ingestion_source = 'kafka'`).

### Prerequisites

- **Kafka** reachable from your Databricks cluster (set `kafka.bootstrap_servers` and `kafka.topic_transactions` in config).
- **Synthetic producer:** Run `scripts/kafka_synthetic_producer.py` (e.g. on your laptop or a server) to send JSON messages to the topic. See `scripts/README_synthetic_producer.md`.

### Run the streaming job

1. Open **`notebooks/06_stream_ingestion_kafka.py`**, set `os.chdir` to your repo path, then run the cell.
2. The notebook starts a **Structured Streaming** query that reads from Kafka, parses JSON (transaction_id, Time, V1–V28, Amount, Class), adds `ingestion_ts` and `ingestion_source = 'kafka'`, and appends to **`bronze_transactions`**.
3. The cell blocks until you **Cancel** the run. While it runs, start the producer to send messages; they will be written to Bronze.
4. To process new Bronze data into Silver/Gold, run **`02_silver_layer`** and **`03_gold_layer`** (on a schedule or manually). Optionally score new Silver rows with **`05_batch_inference`**.

See **`docs/STREAMING.md`** for more detail and optional real-time scoring via Model Serving.

---

For detailed design and later phases, see `IMPLEMENTATION_PLAN.md`.

