# ================================================================
# Exports Gold DuckDB tables as Parquet to Azure gold container.
#
# Run this after dbt build completes successfully.
# Databricks analytics notebooks read from the gold container.
#
# Flow: ucl_gold.duckdb → Parquet bytes → Azure gold/
# ================================================================

import io
import pandas as pd
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError
import duckdb
from utils.config import AZURE_GOLD_CONTAINER, AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_KEY
from utils.logger import get_logger
from datetime import datetime


logger = get_logger(__name__)

DUCKDB_PATH = "data/ucl_gold.duckdb"

GOLD_TABLES = {
    "main_marts.ucl_standings": "standings/",
    "main_marts.top_scorers": "scorers/",
    "main_marts.team_form": "form/",
}


def export_table_to_parquet_bytes(conn: duckdb.DuckDBPyConnection, table_name: str) -> bytes | None:
    """
    Read a DuckDB table and serialise it to Parquet bytes. Uses pyarrow via pandas for serialisation.
    Args:
        conn       : open DuckDB connection
        table_name : fully qualified table name e.g. marts.ucl_standings
    Returns: Parquet bytes or None if failed
    """
    try:
        df = conn.execute(f"SELECT * FROM {table_name}").df()
        buffer = io.BytesIO()
        df.to_parquet(buffer, engine='pyarrow',
                      index=False, compression='snappy')
        buffer.seek(0)
        logger.info(
            f"Serialised {table_name}: {len(df)} rows, {len(df.columns)} cols")
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"Failed to serialise {table_name}: {e}")
        return None


def upload_gold_tables() -> bool:
    """
    Export all Gold DuckDB tables as Parquet and upload to Azure.

    Returns:
        True  if all tables uploaded successfully
        False if any upload failed
    """
    logger.info("=" * 60)
    logger.info("Uploading Gold tables to Azure ADLS Gen2")
    logger.info(f"DuckDB path : {DUCKDB_PATH}")
    logger.info(f"Container   : {AZURE_GOLD_CONTAINER}")
    logger.info("=" * 60)

    # DuckDB connection
    try:
        conn = duckdb.connect(DUCKDB_PATH, read_only=True)
        logger.info(f"Connected to DuckDB: {DUCKDB_PATH}")

    except Exception as e:
        logger.error(f"Failed to open DuckDB: {e}")
        logger.info("Have you run dbt build first?")
        return False

    # Azure Connection String
    conn_str = (
        f"DefaultEndpointsProtocol=https;"
        f"AccountName={AZURE_STORAGE_ACCOUNT};"
        f"AccountKey={AZURE_STORAGE_KEY};"
        f"EndpointSuffix=core.windows.net"
    )
    try:
        az_client = BlobServiceClient.from_connection_string(conn_str)
    except AzureError as e:
        logger.error(f"Failed to connect to Azure Blob Storage: {e}")
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    results = {}

    for table_name, blob_prefix in GOLD_TABLES.items():
        # Build blob path — e.g. standings/gold_ucl_standings_2026-06-03.parquet
        short_name = table_name.split(".")[-1]
        blob_path = (f"{blob_prefix} gold_{short_name}_{today}.parquet"
                     )

        logger.info(f"Exporting: {table_name} -> {blob_path}")

        # Serialise to Parquet bytes
        parquet_bytes = export_table_to_parquet_bytes(conn, table_name)

        if not parquet_bytes:
            results[table_name] = False
            continue

        # Upload to Azure gold container
        try:
            blob_client = az_client.get_blob_client(
                container=AZURE_GOLD_CONTAINER,
                blob=blob_path,
            )
            blob_client.upload_blob(parquet_bytes, overwrite=True)
            size_kb = len(parquet_bytes) / 1024
            logger.info(
                f"Uploaded: {AZURE_GOLD_CONTAINER}/{blob_path} "
                f"({size_kb:.1f} KB)"
            )
            results[table_name] = True

        except Exception as e:
            logger.error(f"Upload failed for {table_name}: {e}")
            results[table_name] = False

    conn.close()

    # Summary
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    logger.info("=" * 60)
    logger.info(f"Upload complete: {success_count}/{total_count} tables")
    for table, ok in results.items():
        status = "OK" if ok else "FAILED"
        logger.info(f"  {status} | {table}")
    logger.info("=" * 60)

    return all(results.values())


if __name__ == "__main__":
    result = upload_gold_tables()
    print(
        f"\nUpload result: "
        f"{'SUCCESS' if result else 'FAILED'}"
    )
