# This python script is used to download the silver data from Azure ADLS Gen2 to local machhine. so dbt can read them via DuckDB.

import os
from utils.config import AZURE_STORAGE_KEY, AZURE_STORAGE_ACCOUNT, AZURE_SILVER_CONTAINER
from utils.logger import get_logger
from azure.storage.blob import BlobServiceClient

logger = get_logger(__name__)

SILVER_LOCAL_DIR = "data/silver_local"


def download_silver_files() -> bool:

    logger.info("=" * 60)
    logger.info("Downloading Silver files from Azure ADLS Gen2")
    logger.info(f"Container : {AZURE_SILVER_CONTAINER}")
    logger.info(f"Local dir : {SILVER_LOCAL_DIR}")
    logger.info("=" * 60)

    os.makedirs(SILVER_LOCAL_DIR, exist_ok=True)

    conn_str = f"DefaultEndpointsProtocol=https;AccountName={AZURE_STORAGE_ACCOUNT};AccountKey={AZURE_STORAGE_KEY};EndpointSuffix=core.windows.net"

    client = BlobServiceClient.from_connection_string(conn_str=conn_str)

    container_client = client.get_container_client(AZURE_SILVER_CONTAINER)

    # list all blobs inside the silver container

    parquet_blobs = [
        b.name for b in container_client.list_blobs() if b.name.endswith(".parquet")]

    if not parquet_blobs:
        logger.error("No Parquet files found in Silver container")
        logger.info("Have you completed Phase 3 Silver transformation?")
        return False

    logger.info(f"Found {len(parquet_blobs)} Parquet files in Silver:")
    for name in parquet_blobs:
        logger.info(f" - {name}")

    # download each parquet file to local dir
    results = {}

    for blob_name in parquet_blobs:
        local_filename = blob_name.replace("/", "_")
        local_path = os.path.join(SILVER_LOCAL_DIR, local_filename)

        if os.path.exists(local_filename):
            size_kb = os.path.getsize(local_filename) / 1024
            logger.info(
                f"File already exists locally: {local_filename} ({size_kb:.2f} KB) - skipping download")
            results[blob_name] = True
            continue

        try:
            blob_client = client.get_blob_client(
                container=AZURE_SILVER_CONTAINER, blob=blob_name)
            raw_bytes = blob_client.download_blob().readall()

            with open(local_path, "wb") as f:
                f.write(raw_bytes)

            size_kb = len(raw_bytes) / 1024

            logger.info(f"Downloaded: {local_filename} ({size_kb:.1f} KB)")

            results[blob_name] = True

        except Exception as e:
            logger.error(f"Failed to download {blob_name}: {e}")
            results[blob_name] = False

    # Summary
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    logger.info("=" * 60)
    logger.info(f"Download complete: {success_count}/{total_count} files")
    logger.info(f"Local path: {os.path.abspath(SILVER_LOCAL_DIR)}")

    # ── Show final file listing
    local_files = sorted(os.listdir(SILVER_LOCAL_DIR))
    logger.info("Files now in data/silver_local/:")
    for filename in local_files:
        filepath = os.path.join(SILVER_LOCAL_DIR, filename)
        size_kb = os.path.getsize(filepath) / 1024
        logger.info(f"  {filename} ({size_kb:.1f} KB)")

    return all(results.values())


if __name__ == "__main__":
    result = download_silver_files()
    print(
        f"\nDownload result: "
        f"{'SUCCESS' if result else 'FAILED'}"
    )
