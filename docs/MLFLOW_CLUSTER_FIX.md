# Fix: CONFIG_NOT_AVAILABLE spark.mlflow.modelRegistryUri

On **Databricks Serverless** or some **free-tier** clusters, Spark does not have `spark.mlflow.modelRegistryUri` set. Any use of Spark (e.g. `spark.table()`) can then fail with:

```text
[CONFIG_NOT_AVAILABLE] Configuration spark.mlflow.modelRegistryUri is not available. SQLSTATE: 42K01
```

## If you use **Serverless** compute

**Spark and Advanced options are not available** for Serverless. You cannot set `spark.mlflow.modelRegistryUri` there. Use the **standalone training** path below (export Silver via SQL, then train from file).

## If you use a **classic (all-purpose) cluster**

1. Go to **Compute** → select your cluster → **Edit** (or **Configuration**).
2. Open **Advanced options**.
3. Under **Spark**, add:
   - **Key:** `spark.mlflow.modelRegistryUri`
   - **Value:** `databricks`
4. Save and restart the cluster.

Then the normal training notebook (with `spark.table()`) should work.

## Alternative: Train without Spark (works on Serverless)

Use this when you're on **Serverless** or cannot change cluster config.

### Step 1: Export Silver data using SQL (no Spark in your notebook)

1. In Databricks, open **SQL Editor** (or **SQL** → **SQL Editor**).
2. Select your **SQL Warehouse** (e.g. "Serverless Starter Warehouse") as the warehouse.
3. Run:
   ```sql
   SELECT * FROM workspace.fraud.silver_transactions
   ```
   (Replace `workspace.fraud` with your catalog and schema if different.)
4. In the results panel, use **Download** / **Export** (e.g. "Download as CSV" or "Download full results") and save the file (e.g. `silver_transactions.csv`).
5. Upload that file to your project Volume:
   - Go to **Catalog** → **workspace** → **fraud** → your Volume (e.g. **fraud_data**).
   - Use **Upload** and upload `silver_transactions.csv` into a folder, e.g. `export/`.
   - Note the full path, e.g. `/Volumes/workspace/fraud/fraud_data/export/silver_transactions.csv`.

### Step 2: Point config at the exported file

In `config/config_dev.yaml`, add (uncomment and set the path to match your file):

```yaml
ml:
  training_data_path: /Volumes/workspace/fraud/fraud_data/export/silver_transactions.csv
```

### Step 3: Re-run the training notebook

Run **`04_ml_training`** again. It will catch the config error and run the standalone trainer (no Spark) using the CSV. The model is written under `storage.base_path/models/` (e.g. `fraud_model.pkl` and `feature_cols.json`).
