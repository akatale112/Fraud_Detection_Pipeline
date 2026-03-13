# Financial Fraud Detection Data Pipeline — Implementation Plan

**Project:** Financial Fraud Detection Data Pipeline  
**Target Platform:** Databricks  
**Last Updated:** March 2025  

---

## 1. Project Objective

Build an end-to-end fraud detection pipeline that:

- Ingests transaction data in **batch** (from Kaggle Credit Card Fraud dataset) and **streaming** (via Kafka)
- Transforms and validates data using a **medallion architecture** (Bronze → Silver → Gold)
- Generates **fraud-related business insights** and dashboard-ready outputs
- Trains and serves a **machine learning model** for fraud detection with **real-time low-latency inference**
- Is fully deployable and orchestrated within **Databricks**

---

## 2. Scope

| In Scope | Out of Scope |
|----------|--------------|
| Batch + streaming ingestion | Custom security / RBAC / multi-tenancy |
| Kaggle Credit Card Fraud dataset as source | External BI tools (Tableau, Power BI) |
| Kafka for streaming | SLA or cost guarantees |
| Full medallion (Bronze / Silver / Gold) from scratch | Compliance / audit logging requirements |
| Data quality checks and validations | Deployment outside Databricks |
| Feature engineering for fraud | |
| ML training, MLflow, model registry | |
| Real-time low-latency inference (model serving) | |
| Dashboards only within Databricks (SQL + Dashboards) | |
| Databricks Workflows and/or Delta Live Tables | |

---

## 3. Clarification: Workflows vs Delta Live Tables (Question 4 Explained)

**What was asked:** Prefer **Databricks Workflows** only, or use **Delta Live Tables (DLT)** for the ETL/medallion layers?

**Explanation:**

- **Databricks Workflows (Jobs):** You author pipelines as **notebooks or Python scripts** that run as job tasks. You define the order of tasks (e.g., ingest → Bronze → Silver → Gold) and schedule or trigger them. You write **explicit PySpark/Spark SQL** for each step. Full control; good when you want custom logic and visibility into every line of code.

- **Delta Live Tables (DLT):** You define pipelines **declaratively** using SQL or PySpark in DLT syntax. DLT manages scheduling, retries, and **built-in data quality expectations** (e.g., `EXPECT` clauses). It is optimized for medallion-style ETL and simplifies incremental processing. Less boilerplate; good when you want a standard medallion pattern and built-in quality checks.

**Recommendation for this project:** Use **both** in a hybrid way:

- **DLT** for the **medallion ETL** (Bronze → Silver → Gold): consistent structure, built-in expectations, less custom orchestration code.
- **Databricks Workflows** for: (1) **ingestion** (e.g., pulling from Kaggle/cloud storage into a landing zone and/or publishing to Kafka), (2) **ML training and inference** jobs, (3) **orchestrating** DLT pipeline runs and post-ETL steps (e.g., trigger DLT, then run training job).

This keeps ETL maintainable and dashboard-ready while leaving ML and ingestion in flexible, code-first workflows.

---

## 4. Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Ingest transaction data in **batch** from Kaggle Credit Card Fraud dataset (e.g., from cloud storage/DBFS). | Must |
| FR-2 | Ingest transaction data in **streaming** mode from **Kafka** (e.g., same schema as batch). | Must |
| FR-3 | Store raw data in **Bronze** (append-only, immutable). | Must |
| FR-4 | Transform and validate data into **Silver** (cleaned, deduplicated, typed). | Must |
| FR-5 | Build **Gold** layer: aggregates, KPIs, and tables ready for dashboards. | Must |
| FR-6 | Run **data quality checks** (schema, completeness, validity, uniqueness) with configurable behavior (fail/warn/log). | Must |
| FR-7 | Perform **fraud-specific feature engineering** and expose features for ML. | Must |
| FR-8 | **Train** a binary fraud detection model; log experiments and register model in **MLflow**. | Must |
| FR-9 | Support **real-time low-latency inference** (e.g., Databricks Model Serving or similar). | Must |
| FR-10 | Provide **batch inference** option (e.g., score new Silver/Gold data in a job). | Should |
| FR-11 | **Dashboard** outputs only within Databricks (SQL + Dashboards on Gold). | Must |
| FR-12 | Orchestrate pipeline via **Databricks Workflows** and optionally **DLT**. | Must |

---

## 5. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Pipeline runs must be **idempotent** and **replayable** where applicable. |
| NFR-2 | Use **Delta Lake** for all persistent tables (ACID, time travel, schema evolution). |
| NFR-3 | **Logging** and basic **monitoring** (e.g., job run status, row counts) in place. |
| NFR-4 | **Documentation** (README, config, and high-level architecture) in repo. |
| NFR-5 | **No specific SLA** or latency guarantees required. |
| NFR-6 | **No custom security** (RBAC, row-level security) required. |

---

## 6. Proposed Architecture (High Level)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                            │
├──────────────────────────────┬──────────────────────────────────────────────────┤
│  Batch: Kaggle CC Fraud      │  Streaming: Kafka (transaction events)            │
│  (CSV/Parquet → cloud/DBFS)  │  (same schema, continuous feed)                   │
└──────────────┬───────────────┴────────────────────┬─────────────────────────────┘
               │                                     │
               ▼                                     ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                     INGESTION (Workflows / Spark jobs)                             │
│  Batch: read from path → write to landing/Bronze  │  Stream: Kafka → Bronze       │
└──────────────────────────────┬───────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                    MEDALLION (DLT or Workflow tasks)                               │
│  BRONZE (raw, append-only) → SILVER (clean, deduped) → GOLD (aggregates, KPIs)   │
│  + Data quality expectations + Feature engineering                                │
└──────────────────────────────┬───────────────────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────────┐
│  Dashboards      │ │  ML Training     │ │  Real-time inference         │
│  (Databricks     │ │  (Workflows +    │ │  (Model Serving / API)       │
│   SQL +          │ │   MLflow)        │ │  + Batch inference job        │
│   Dashboards)    │ │                  │ │                               │
└──────────────────┘ └──────────────────┘ └──────────────────────────────┘
```

---

## 7. Data Flow (Ingestion → Insights / Modeling)

| Step | Description |
|------|-------------|
| 1. **Batch ingestion** | Job reads Kaggle Credit Card Fraud data (e.g., from DBFS or S3 path); writes raw records into Bronze table(s) or a landing path that DLT reads. |
| 2. **Streaming ingestion** | Structured Streaming job reads from Kafka; writes micro-batches into the same Bronze table (or a dedicated Kafka-backed Bronze). |
| 3. **Bronze → Silver** | DLT (or Spark job): parse, validate schema, cast types, deduplicate by `transaction_id` (or equivalent), apply data quality expectations. Optionally mask/hash PII if needed later. |
| 4. **Silver → Gold** | DLT (or Spark job): aggregate by time, customer, merchant; compute fraud rates, amounts, counts; build feature tables and dashboard-ready summary tables. |
| 5. **Gold / Features → ML** | Training job reads from Silver + Gold (feature table); trains binary classifier; logs to MLflow; registers best model. |
| 6. **Inference** | **Real-time:** Model Serving endpoint serves single or small-batch requests. **Batch:** Job reads new Silver/Gold rows; scores; writes to `gold_transaction_scores` or similar. |
| 7. **Dashboards** | Databricks SQL and Dashboards query Gold tables for KPIs, trends, and alerts. |

**Real-time inference flow (Step 6):** A **synthetic producer script** (`scripts/kafka_synthetic_producer.py`) runs outside (or inside) Databricks: it generates transactions with a configurable fraud rate and publishes JSON messages to a Kafka topic. The streaming job ingests from Kafka into Bronze; each new transaction can be sent to **Databricks Model Serving** for low-latency fraud score; scores may be written back to Gold for dashboards.

---

## 8. Medallion Architecture Design

| Layer | Table(s) | Purpose | Key Columns (example) |
|-------|----------|---------|------------------------|
| **Bronze** | `bronze_transactions` | Raw ingestion; one row per event. | `payload` (or individual columns mirroring source), `ingestion_ts`, `source` (batch/kafka), `topic` (if Kafka). |
| **Silver** | `silver_transactions` | Cleaned, validated, deduplicated transactions. | `transaction_id`, `timestamp`, `amount`, `customer_id`, `merchant`, `label` (if present), `ingestion_ts`. |
| **Gold** | `gold_fraud_daily_summary` | Daily fraud KPIs. | `date`, `total_txn`, `fraud_count`, `fraud_rate`, `total_amount`, `fraud_amount`. |
| **Gold** | `gold_customer_risk` | Per-customer aggregates for dashboards. | `customer_id`, `txn_count`, `fraud_count`, `total_amount`, `window`. |
| **Gold** | `gold_transaction_scores` | Model scores (batch + optional real-time write-back). | `transaction_id`, `score`, `prediction`, `model_version`, `scored_at`. |

- **Bronze:** Append-only; partition by ingestion date (or similar).
- **Silver:** Dedupe by business key; partition by date.
- **Gold:** Partition by date or dimension as needed; optimize + z-order for dashboard queries.

---

## 9. Dataset: Kaggle Credit Card Fraud + Kafka

| Aspect | Detail |
|--------|--------|
| **Batch source** | [Kaggle: Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) — CSV with anonymized features (V1–V28, `Time`, `Amount`) and binary `Class` (0/1). |
| **Streaming source** | **Kafka** — same schema (or equivalent) produced by a **synthetic data producer script** that generates transactions and injects fraud at a configurable rate. |
| **Implications** | Pipeline must handle (1) CSV/Parquet for batch, (2) Kafka topic(s) for streaming; schema alignment between both paths. A **Kafka synthetic producer** (`scripts/kafka_synthetic_producer.py`) generates Kaggle-like records (Time, V1–V28, Amount, Class), injects fraud, and streams to Kafka for real-time ingestion and inference testing. |

---

## 10. Batch vs Streaming Implementation Options

| Mode | Trigger | Implementation | Output |
|------|---------|-----------------|--------|
| **Batch** | Scheduled (e.g., daily) or manual | Workflow task: read from cloud/DBFS path → write to Bronze (or landing for DLT). DLT then processes new data. | Same Bronze/Silver/Gold tables. |
| **Streaming** | Continuous (24/7 or long-running job) | Structured Streaming from Kafka → write to Bronze. DLT pipeline can be run in **continuous** or **triggered** mode to process Bronze → Silver → Gold. | Same Silver/Gold tables; lower latency. |

- **Shared logic:** Silver and Gold transformations are defined once; both batch and streaming feed the same Bronze, so DLT or a single set of Spark jobs can process both.
- **Kafka:** Use Databricks Kafka connector (or Spark Kafka source); credentials via secrets.

---

## 11. Fraud-Related Transformations and Feature Engineering

- **Time:** `hour_of_day`, `day_of_week`, `is_weekend`, `seconds_since_epoch` (from `Time`).
- **Amount:** `log_amount`, `amount_bin`; z-score or percentile by customer/segment if identifiers exist.
- **Velocity:** For Kaggle schema, use `Time` to derive transaction counts per time window (e.g., per hour) if we can define a “customer” (e.g., from a derived or synthetic ID).
- **Aggregates:** Rolling count/sum of transactions in last 1h/24h (in Silver or Gold).
- **Risk flags:** `high_value` (e.g., amount > percentile 95), `off_hours`, velocity spike (e.g., count in last hour >> baseline).
- **Model features:** Subset of V1–V28 + `Time`, `Amount` + derived features above; stored in Silver or a dedicated **feature table** for training and serving.
- **Label:** Kaggle `Class` (0/1) used as target for training; in production, label may be delayed (e.g., chargebacks) and used for retraining.

---

## 12. Data Quality Checks and Validations

| Check | Layer | Rule | Action |
|-------|--------|------|--------|
| Schema | Bronze → Silver | Expected columns and types | Fail or drop invalid rows |
| Completeness | Silver | Non-null `transaction_id`, `amount`, `Time` | Drop or quarantine |
| Validity | Silver | `amount` > 0; `Time` in range; `Class` in {0,1} | Drop or flag |
| Uniqueness | Silver | No duplicate `transaction_id` | Dedupe (e.g., latest only) |
| Freshness | Monitoring | Latest partition timestamp vs now | Alert (optional) |

Implementation: **DLT expectations** (e.g., `EXPECT ... ON VIOLATION DROP ROW`) or **Great Expectations** in a Spark job; configurable per environment.

---

## 13. Storage and Table Design

| Aspect | Choice |
|--------|--------|
| **Format** | Delta for all layers. |
| **Bronze partitioning** | By `ingestion_date` (yyyy-MM-dd). |
| **Silver partitioning** | By `date` (derived from `Time` or ingestion). |
| **Gold partitioning** | By `date` for time-series aggregates. |
| **Optimize** | Periodic `OPTIMIZE` + `Z-ORDER BY` on filter columns (e.g., `date`, `customer_id`, `Class`). |
| **Retention** | Configurable (e.g., Bronze 90 days, Silver/Gold longer); no strict requirement from project. |

---

## 14. ML Training and Inference Design

| Component | Design |
|-----------|--------|
| **Training data** | Built from Silver + Gold feature table; time-based or random split; target = `Class`. |
| **Algorithm** | Binary classifier (e.g., Logistic Regression, XGBoost, or Random Forest) — sklearn or Spark ML. |
| **MLflow** | Log params, metrics (precision, recall, F1, AUC-ROC), and model artifact; register to Model Registry (e.g., “Staging”). |
| **Batch inference** | Job: read new Silver/Gold rows → load registered model → score → write to `gold_transaction_scores`. |
| **Real-time inference** | **Databricks Model Serving** (or equivalent): deploy registered model as REST endpoint; single-row or small-batch requests; low-latency. Optionally write scored transactions back to Gold. |
| **Feature store** | Optional: Databricks Feature Store for consistent features between training and real-time serving. |

---

## 15. Experiment Tracking and Evaluation

- **MLflow Tracking:** All training runs log parameters, metrics, and model.
- **Metrics:** Precision, recall, F1, AUC-ROC; optional cost-weighted metric.
- **Validation:** Holdout set; prefer time-based split if `Time` reflects order.
- **Model Registry:** Promote best model (e.g., by F1 or AUC) to Staging → Production; Model Serving uses Production version.

---

## 16. Dashboard and Insight Outputs (Databricks Only)

- **Gold tables** used by Databricks SQL and Dashboards:
  - Fraud rate and transaction volume over time (daily/hourly).
  - Top risky segments (if dimensions available from features).
  - Amount distribution and high-value fraud share.
  - Model performance over time (e.g., precision/recall from batch inference results).
  - Data quality summary (e.g., row counts, drop counts from DQ).
- **No** export to external BI; all consumption within Databricks.

---

## 17. Deployment Plan in Databricks

| # | Activity |
|---|----------|
| 1 | **Repos:** Project in Databricks Repos (or Git sync); notebooks, `src/`, `config/` in repo. |
| 2 | **Cluster:** Shared or separate clusters for ETL vs ML; policy for node type and autoscaling. |
| 3 | **DLT pipeline:** Create DLT pipeline definition (Bronze → Silver → Gold); run in triggered or continuous mode. |
| 4 | **Workflows:** (a) Batch ingestion job; (b) DLT pipeline run (or scheduled); (c) ML training job; (d) Batch inference job; (e) Optional: Kafka streaming job as separate long-running job. |
| 5 | **Model Serving:** Enable Model Serving for the registered fraud model; configure endpoint for real-time inference. |
| 6 | **Secrets:** Kafka credentials and any API keys in Databricks secrets. |
| 7 | **Dashboards:** Create SQL queries and Dashboards in Databricks workspace on Gold tables. |

---

## 18. Testing Strategy

| Type | Scope |
|------|--------|
| **Unit** | Pytest for pure Python (e.g., feature functions, validation helpers). |
| **Integration** | Run Bronze → Silver → Gold on small fixture (subset of Kaggle) in test workspace. |
| **Data quality** | Assert expectations on fixture data (e.g., no duplicates in Silver, valid ranges). |
| **ML** | Test model load and prediction shape on sample input; optional smoke test for Model Serving. |
| **No production data** | Use only Kaggle sample or synthetic data in tests. |

---

## 19. Repo / Folder Structure (Proposed)

```
financial-fraud-detection/
├── README.md
├── IMPLEMENTATION_PLAN.md          # This document
├── config/
│   ├── config_dev.yaml
│   └── config_prod.yaml
├── src/
│   ├── ingestion/
│   │   ├── batch_ingest.py
│   │   └── stream_ingest.py
│   ├── transform/
│   │   ├── bronze_to_silver.py
│   │   └── silver_to_gold.py
│   ├── quality/
│   │   └── expectations.py
│   ├── features/
│   │   └── fraud_features.py
│   └── ml/
│       ├── train.py
│       └── inference.py
├── dlt/
│   └── dlt_pipeline.py             # DLT definitions (Bronze/Silver/Gold)
├── notebooks/
│   ├── 01_batch_ingestion.py
│   ├── 02_stream_ingestion_kafka.py
│   ├── 03_ml_training.py
│   └── 04_batch_inference.py
├── resources/
│   ├── workflow_batch.json
│   ├── workflow_streaming.json
│   └── dlt_pipeline_config.json
├── tests/
│   ├── unit/
│   └── integration/
├── scripts/
│   ├── kafka_synthetic_producer.py # Synthetic transaction + fraud generator → Kafka (for streaming + real-time inference)
│   └── README_synthetic_producer.md
└── docs/
    └── architecture.md
```

---

## 20. Risks, Assumptions, and Open Questions

| Item | Description |
|------|-------------|
| **Kafka availability** | Kafka cluster (e.g., Confluent Cloud, self-hosted, or Databricks-managed) is available; topic and schema agreed. |
| **Kaggle access** | Dataset is downloaded and placed in cloud/DBFS or accessible via API; no strict automation for Kaggle login in plan. |
| **Real-time latency** | “Low latency” achieved via Model Serving; exact P99 target not specified (no SLA). |
| **Labels in production** | In production, fraud labels may be delayed; pipeline assumes batch retraining with latest labels when available. |
| **Open** | Whether to use **Databricks Feature Store** for real-time serving (recommended if many derived features). |

---

## 21. Suggested Milestones

| Milestone | Deliverables |
|-----------|--------------|
| **M1: Foundation** | Repo structure; config; Kaggle dataset in DBFS; Kafka topic and simulator (if needed); dev cluster. |
| **M2: Bronze + Silver** | Batch ingestion to Bronze; DLT or Spark Silver layer with DQ; deduplication and schema. |
| **M3: Gold + Dashboards** | Gold tables; fraud KPIs; at least one Databricks Dashboard. |
| **M4: ML training** | Feature table; training notebook/job; MLflow logging and model registration. |
| **M5: Inference** | Batch inference job; Model Serving endpoint for real-time inference. |
| **M6: Streaming** | Kafka streaming ingestion to Bronze; DLT or job processing stream into Silver/Gold. |
| **M7: Orchestration** | Workflows for batch, streaming, training, and inference; documentation and handover. |

---

## 22. Phase-wise Implementation Plan

This section summarizes the implementation in clear phases. Each phase can be developed, tested, and deployed incrementally.

### Phase 0: Setup & Environment

- **Goals**
  - Have a working Databricks environment and Kafka setup.
  - Prepare repo and base configuration for the project.
- **Key tasks**
  - Create / configure Databricks workspace, clusters, and DBFS paths.
  - Set up Git repository and connect to Databricks Repos.
  - Provision or connect to a Kafka cluster (topic for `transactions`).
  - Download Kaggle Credit Card Fraud dataset and place it in DBFS or cloud storage.
  - Configure secrets (Kafka credentials, if needed).

### Phase 1: Batch Ingestion & Bronze Layer

- **Goals**
  - Ingest Kaggle dataset in batch and store raw data in Bronze tables.
- **Key tasks**
  - Implement a batch ingestion notebook/script that reads Kaggle CSV/Parquet from DBFS/cloud storage.
  - Write raw records (with ingestion metadata) into `bronze_transactions` (Delta).
  - Add basic logging and row-count checks for the ingestion job.
  - Create a Databricks Workflow job to run batch ingestion on demand or on schedule.

### Phase 2: Silver Layer (Cleaning, DQ, and Standardization)

- **Goals**
  - Turn raw Bronze data into a clean, deduplicated, and validated Silver table.
- **Key tasks**
  - Define Silver schema for `silver_transactions` (types, required columns).
  - Implement Bronze → Silver transformation (DLT pipeline or PySpark job):
    - Type casting, null checks, value checks (e.g., amount > 0, Class in {0,1}).
    - Deduplication on `transaction_id` (or an equivalent key).
    - Data quality expectations (schema/completeness/validity/uniqueness).
  - Store clean records in `silver_transactions` Delta table.
  - Wire this step into either:
    - DLT pipeline referencing Bronze as source, or
    - A Workflow task that runs after batch ingestion.

### Phase 3: Gold Layer (KPIs, Aggregates, and Dashboard Tables)

- **Goals**
  - Build Gold tables that are easy to query for business insights and dashboards.
- **Key tasks**
  - Design Gold tables such as:
    - `gold_fraud_daily_summary` (daily counts, fraud rate, amounts).
    - `gold_transaction_scores` (for model outputs, added in Phase 5).
  - Implement Silver → Gold transformations (aggregations and derivations).
  - Partition and optimize Gold tables for common queries (e.g., by `date`).
  - Create initial Databricks SQL queries and simple dashboards using Gold tables.

### Phase 4: Feature Engineering & ML Training

- **Goals**
  - Build ML-ready features and train a first fraud detection model.
- **Key tasks**
  - Implement feature engineering logic (time features, amount features, simple velocity features).
  - Create a training dataset from `silver_transactions` (and optional feature tables).
  - Use MLflow to:
    - Train a binary classifier (e.g., Logistic Regression/XGBoost).
    - Log parameters, metrics (precision, recall, F1, AUC), and artifacts.
    - Register the best model in the MLflow Model Registry.
  - Add a training notebook/job and integrate it into Workflows (manual or scheduled).

### Phase 5: Inference (Batch + Real-time Preparation)

- **Goals**
  - Score transactions with the trained model and prepare for real-time serving.
- **Key tasks**
  - Implement a batch inference job:
    - Read new `silver_transactions`.
    - Apply the registered model.
    - Write results to `gold_transaction_scores` (including score, prediction, model version, and timestamp).
  - Set up Databricks Model Serving endpoint using the registered Production model.
  - Define input schema for real-time requests (matching synthetic/Kafka message schema).
- **Implemented**
  - **Batch inference:** `src/ml/inference.run_batch_inference()` and notebook `notebooks/05_batch_inference.py` (read Silver, load model from `storage.base_path/models/`, score, write to `gold_transaction_scores`).
  - **Real-time schema:** `REALTIME_INPUT_SCHEMA` in `src/ml/inference.py`; Model Serving setup and request format documented in `docs/MODEL_SERVING.md`.

### Phase 6: Streaming Ingestion with Kafka & Real-time Flow

- **Goals**
  - Ingest synthetic streaming data from Kafka into the medallion pipeline and support low-latency scoring.
- **Key tasks**
  - Use `scripts/kafka_synthetic_producer.py` to generate synthetic transactions (including fraud) and send them to a Kafka topic.
  - Implement a Structured Streaming job in Databricks:
    - Read JSON messages from Kafka.
    - Parse records and write to `bronze_transactions` (or a Kafka-specific Bronze table).
  - Reuse Bronze → Silver → Gold logic for streaming (or configure DLT for streaming mode).
  - Connect the streaming job or a downstream process to the Model Serving endpoint to score events in near real time.
  - Optionally write scored streaming results back into `gold_transaction_scores` for dashboards.

### Phase 7: Orchestration, Monitoring, and Documentation

- **Goals**
  - Operationalize the pipeline end to end and document it.
- **Key tasks**
  - Build Databricks Workflows that chain tasks:
    - Batch ingestion → Bronze → Silver → Gold → Training → Batch inference.
    - Separate streaming workflow for Kafka ingestion and streaming processing.
  - Configure basic monitoring:
    - Job run status and alerts.
    - Row counts and DQ metrics on key steps.
  - Finalize documentation:
    - Update `README.md`, architecture diagrams, and usage instructions.
    - Document how to run the synthetic producer, streaming job, and real-time inference.

---

## 22. Suggested Tech Stack (Summary)

| Layer | Technology |
|-------|------------|
| Language | Python 3.10+ |
| Processing | PySpark 3.x |
| Storage | Delta Lake |
| Orchestration | Databricks Workflows + Delta Live Tables (for medallion) |
| Streaming | Structured Streaming + Kafka |
| ML | MLflow, sklearn / XGBoost / Spark ML |
| Real-time serving | Databricks Model Serving |
| DQ | DLT expectations or Great Expectations |
| Dashboards | Databricks SQL + Dashboards |
| Repo | Databricks Repos + Git |

---

## Next Step

This plan is fixed per your answers: **Kaggle + Kafka**, **real-time low-latency inference**, **full medallion from scratch**, **no security**, **Databricks-only dashboards**, **no SLA**.

When you are ready for implementation, say **“Start implementing”** and implementation will begin according to this plan and the agreed repo structure.
