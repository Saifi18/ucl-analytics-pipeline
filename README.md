# 🏆 UCL Analytics Pipeline

End-to-end Champions League data engineering pipeline.

## Architecture

Source (UCL API) → Bronze (Azure ADLS Gen2) → Silver (PySpark) → Gold (dbt + DuckDB) → Analytics (Databricks CE)

## Tech Stack

| Tool              | Purpose                     | Layer              |
| ----------------- | --------------------------- | ------------------ |
| Azure ADLS Gen2   | Cloud data lake storage     | All                |
| Databricks CE     | PySpark compute + notebooks | Silver + Analytics |
| PySpark           | Distributed transformations | Silver             |
| Delta Lake        | ACID table format           | Silver             |
| dbt Core          | SQL Gold models + tests     | Gold               |
| DuckDB            | Analytics query engine      | Gold               |
| football-data.org | UCL match data API          | Source             |

## Status

🚧 Phase 1 — Foundation complete
