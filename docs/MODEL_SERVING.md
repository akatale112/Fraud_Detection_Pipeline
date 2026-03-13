# Databricks Model Serving & Real-Time Inference

Phase 5 implements **batch inference** (notebook `05_batch_inference.py`). This document describes how to set up **real-time low-latency inference** via Databricks Model Serving and the expected request schema.

---

## Batch inference (implemented)

- **Notebook:** `notebooks/05_batch_inference.py`
- **Logic:** `src/ml/inference.run_batch_inference(spark, config_path)`
- Reads from `silver_transactions`, loads the model from `storage.base_path/models/fraud_model.pkl` and `feature_cols.json`, scores each row, and writes to **`gold_transaction_scores`** with columns: `transaction_id`, `score`, `prediction`, `model_version`, `scored_at`.
- Run after Phase 4 (model and feature list must exist). You can schedule this notebook in a Databricks Workflow after training or after Silver updates.

---

## Real-time inference (Model Serving)

To serve the fraud model over HTTP for low-latency scoring (e.g. from Kafka consumers or APIs):

### 1. Register the model in MLflow

The **standalone** training path (Phase 4) saves the model to Volume only. To use Model Serving you need a **registered** model in the workspace:

- **Option A – Log from standalone run:** If you have already run Phase 4 with MLflow tracking (file or Databricks), open **MLflow** → your experiment → the run → **Register model** and create a model name (e.g. `fraud_detection_model`).
- **Option B – Register from file:** In a notebook, load the pickle and feature list from `storage.base_path/models/`, then log and register:

  ```python
  import mlflow
  import joblib
  mlflow.set_tracking_uri("databricks")  # or file:/tmp/mlflow
  with open("<base_path>/models/feature_cols.json") as f:
      feature_cols = json.load(f)["feature_cols"]
  model = joblib.load("<base_path>/models/fraud_model.pkl")
  with mlflow.start_run():
      mlflow.sklearn.log_model(model, "model", registered_model_name="fraud_detection_model")
  ```

Use the same **model name** as in config: `real_time_inference.model_name` (default `fraud_detection_model`).

### 2. Create a Model Serving endpoint

1. In Databricks: **Machine Learning** → **Serving** → **Create serving endpoint**.
2. Select **Model** and choose the registered model (e.g. `fraud_detection_model`) and a version (e.g. latest **Production**).
3. Configure compute and scaling; create the endpoint.
4. Copy the endpoint **URL** and (if needed) **token**.
5. In `config/config_dev.yaml` (or prod), set:
   ```yaml
   real_time_inference:
     model_name: fraud_detection_model
     serving_endpoint: https://<workspace>.databricks.com/serving-endpoints/<endpoint>/invocations
   ```

### 3. Invoke the endpoint

Send **JSON** with the same features the model was trained on. Schema below.

---

## Real-time request schema

The model expects one or more records with **numeric features** matching training (Kaggle-style: `Time`, `Amount`, `V1`–`V28`, plus derived `log_amount`, `time_hour`). For REST you can send **input records**; the serving layer may compute derived features if you deploy a custom wrapper, or you can precompute them client-side.

**Minimal payload (per record):**

- `Time` (number), `Amount` (number), `V1`–`V28` (numbers).  
- If the deployed model was logged with **derived** features, the endpoint input typically expects the **raw** columns and the model’s preprocessing (or a wrapper) adds `log_amount` and `time_hour`. If your registered model is the raw sklearn pipeline that expects already-scaled/derived features, send the same 31 columns as in `feature_cols.json`: `Time`, `Amount`, `V1`–`V28`, `log_amount`, `time_hour`.

**Example single request (Databricks serving often expects a `dataframe_records` or `inputs` key):**

```json
{
  "dataframe_records": [
    {
      "Time": 406,
      "Amount": 50.0,
      "V1": -1.23, "V2": 0.45, "V3": 0.98, "V4": -0.12, "V5": -0.34,
      "V6": 0.56, "V7": 0.21, "V8": -0.09, "V9": 0.11, "V10": -0.22,
      "V11": 0.33, "V12": -0.44, "V13": 0.55, "V14": -0.66, "V15": 0.01,
      "V16": -0.02, "V17": 0.03, "V18": -0.04, "V19": 0.05, "V20": -0.06,
      "V21": 0.07, "V22": -0.08, "V23": 0.09, "V24": -0.10, "V25": 0.11,
      "V26": -0.12, "V27": 0.13, "V28": -0.14,
      "log_amount": 3.93,
      "time_hour": 0.113
    }
  ]
}
```

(Exact key names depend on how the endpoint is configured; see Databricks [Model Serving docs](https://docs.databricks.com/machine-learning/model-serving/index.html).)

**Programmatic schema** (for validation or client code) is defined in `src/ml/inference.py` as **`REALTIME_INPUT_SCHEMA`**: required fields include `Time`, `Amount`, and `V1`–`V28`; optional `Class` for validation. Derived features `log_amount` and `time_hour` can be computed as:

- `log_amount = log(Amount + 1)`
- `time_hour = (Time % 86400) / 3600.0`

---

## Summary

| Component            | Status   | Location / config |
|---------------------|----------|-------------------|
| Batch inference      | Implemented | `notebooks/05_batch_inference.py`, `src/ml/inference.run_batch_inference` |
| Gold scores table   | Written by batch job | `gold_transaction_scores` (transaction_id, score, prediction, model_version, scored_at) |
| Real-time serving   | Manual setup | Register model → Create serving endpoint → set `real_time_inference.serving_endpoint` |
| Request schema      | Documented + code | This doc + `REALTIME_INPUT_SCHEMA` in `src/ml/inference.py` |
