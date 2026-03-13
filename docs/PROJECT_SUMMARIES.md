# Project Summaries

Concise summaries of key projects for resume, portfolio, and interview prep.

---

## 1. Financial Fraud Detection Data Pipeline

**Stack:** Databricks, PySpark, Delta Lake, Unity Catalog, Python, YAML config

**Challenge:** Build an end-to-end pipeline to ingest transaction data, clean and validate it, store it in a structured way, and produce fraud-related KPIs for analytics—with a path to ML-based fraud detection.

**Solution:**
- Implemented a **medallion architecture** (Bronze → Silver → Gold) on Databricks using Delta Lake and Unity Catalog.
- **Bronze:** Batch ingestion of Kaggle Credit Card Fraud dataset with config-driven paths (DBFS/Volumes) and managed tables.
- **Silver:** Data quality (type casting, null checks, validity rules, deduplication) and added `transaction_id` for downstream use.
- **Gold:** Daily fraud KPIs: total transactions, fraud count, fraud rate, total/fraud amounts by date for dashboards.
- Feature engineering (e.g. log amount, time-based features) and modular code (ingestion, transform, config); ML training (scikit-learn + MLflow) planned as next step with Serverless-friendly design.

**Impact:** Unified, reliable fraud analytics layer; clear separation of raw, cleaned, and business-ready data; foundation for model training and real-time inference.

**One-line:** End-to-end fraud detection pipeline on Databricks (medallion, Delta Lake, PySpark); Gold-layer KPIs and feature engineering in place; ML training planned as next step.

---

## 2. Entity Resolution & Record Linkage (Large-Scale Data Integration)

**Stack:** SQL, Apache Spark, PySpark, Databricks, Python, scikit-learn, BERT/BGE embeddings, OpenAI API (GPT)

**Challenge:** Merge and integrate two large datasets (25M+ records each) from disparate sources into a single, deduplicated view for unified analysis.

**Solution:**
- Designed **SQL-based merging and integration** to combine datasets and support unified analytics.
- Implemented **fuzzy matching** and **string matching** for entity resolution and record linkage (same real-world entity across different spellings and formats).
- Applied **NLP and embeddings** (BERT, LLaMA, BGE) for **semantic similarity** so records with different wording but same meaning could be matched—improving match accuracy by ~40%.
- Used **OpenAI API (GPT)** for advanced analysis, entity resolution, and **data enrichment** (e.g. normalizing names, filling gaps).
- Built **Databricks data pipelines** with Spark/PySpark to process merged data at scale.
- Trained **binary classification** models (scikit-learn) to combine multiple signals (fuzzy score, embedding similarity, etc.) into match/no-match decisions.

**Impact:** Unified view of 25M+ records; higher match accuracy via semantic similarity; scalable pipelines and ML-driven linkage supporting downstream analytics and reporting.

**One-line:** Large-scale entity resolution across 25M+ records using SQL merge, fuzzy/string matching, BERT/BGE semantic similarity, GPT enrichment, and scikit-learn classification on Databricks.

---

## 3. Multilingual Sentiment Analysis for E-Commerce

**Stack:** NLP, BERT, Python, REST API, Azure, dashboards (e.g. Power BI / Tableau)

**Challenge:** E-commerce client needed sentiment analysis of customer reviews in multiple Indian languages (Marathi, Hindi, English) to understand feedback at scale.

**Solution:**
- Built a **sentiment analysis system** supporting **Marathi, Hindi, and English** with **language detection**, **text normalization**, and **tokenization** (200K+ reviews).
- Trained **BERT-based sentiment classifiers** per language (or multilingual setup), achieving **87% accuracy** across all three.
- Created a **REST API** that handles language routing, model selection, and **real-time sentiment prediction** (serving 5K+ requests/day).
- Deployed on **Azure** with **auto-scaling** for real-time predictions with **~200 ms average latency**.
- Developed **dashboards** for sentiment trends by language, product category, time period, and region.

**Impact:** 100K+ reviews analyzed across 3 languages; 87% classification accuracy; cloud-deployed, low-latency API enabling automated review analysis for the e-commerce platform.

**One-line:** Multilingual (Marathi, Hindi, English) sentiment analysis using BERT-based classifiers, REST API, and Azure deployment; 87% accuracy, ~200 ms latency, 5K+ requests/day.

---

## 4. Big Data Analytics Pipeline with Apache Spark & Hadoop

**Stack:** Apache Spark, PySpark, Hadoop (HDP), ETL, data lake, data quality monitoring

**Challenge:** Client had siloed data across multiple systems and needed a single platform to transform and analyze it for enterprise decisions.

**Solution:**
- Built a **data pipeline** using **Apache Spark on a Hadoop cluster (HDP)**.
- Implemented **ETL workflows** extracting from **5+ sources** (RDBMS, files, APIs), transforming with **PySpark** (business logic, aggregations), and loading into a **data lake**.
- Added **data quality monitoring** to detect anomalies and schema changes.
- **Optimized Spark jobs** (partitioning, caching, join strategies, etc.), improving performance by **~45%**.

**Impact:** Unified data from disparate sources; **50M+ records processed daily**; processing time reduced from **~8 hours to ~90 minutes**; actionable insights for business decisions.

**One-line:** Spark-on-Hadoop ETL pipeline unifying 5+ sources into a data lake, with quality monitoring and job optimization; 50M+ records/day, run time cut from 8 hours to 90 minutes.

---

## Quick reference

| Project | Core problem | Main tech | Key outcome |
|--------|---------------|-----------|-------------|
| Fraud Detection Pipeline | Reliable fraud analytics + path to ML | Databricks, Delta, medallion, PySpark | Bronze/Silver/Gold + KPIs; ML next |
| Entity Resolution | Merge 25M+ records, match entities | Spark, BERT/BGE, fuzzy match, GPT, scikit-learn | ~40% better match accuracy; unified view |
| Multilingual Sentiment | Sentiment in Marathi, Hindi, English | BERT, REST API, Azure | 87% accuracy; 5K req/day; 200 ms latency |
| Big Data Analytics Pipeline | Siloed data → unified analytics | Spark, Hadoop, ETL, data lake | 50M+ records/day; 8 hr → 90 min |

---

*Use these summaries for resume bullets, LinkedIn, or interview talking points. Adjust numbers and scope to match your actual experience.*
