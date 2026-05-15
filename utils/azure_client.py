# ================================================================
# azure_client.py — Azure ADLS Gen2 storage wrapper
# All Azure SDK interactions live here
# ================================================================

import json
from azure.storage.blob import BlobServiceClient, ContainerClient
from utils.config import AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_KEY
from utils.logger import get_logger

logger = get_logger(__name__)


class AzureStorageClient:
    """
    Wrapper around azure-storage-blob SDK for ADLS Gen2.
    Provides simple upload/download methods for pipeline use.
    """

    def __init__(self):

        # Build connection string from config
        conn_str = (
            f"DefaultEndpointsProtocol=https;"f"AccountName={AZURE_STORAGE_ACCOUNT};"f"AccountKey={AZURE_STORAGE_KEY};"f"EndpointSuffix=core.windows.net")
        self.client = BlobServiceClient.from_connection_string(conn_str)
        logger.info(
            f"AzureStorageClient connected to: {AZURE_STORAGE_ACCOUNT}")

    def upload_json(self, data: dict | list, container: str, blob_path: str) -> bool:
        """
        Upload a Python dict or list as a JSON file to Azure.
        Args:
        data : dict or list to upload
        container : "bronze", "silver", or "gold"
        blob_path : path inside container e.g. "matches/2024-11-01_matches.json"
        Returns: True if successful, False if failed
        """

        try:
            json_bytes = json.dumps(data, indent=2).encode('utf-8')
            blob_client = self.client.get_blob_client(
                container=container, blob=blob_path)
            blob_client.upload_blob(json_bytes, overwrite=True)
            logger.info(
                f"Uploaded JSON → {container}/{blob_path} "f"({len(json_bytes):,} bytes)")
            return True
        except Exception as e:
            logger.error(f"Failed to upload {blob_path}: {e}")
            return False

    def download_json(self, container: str, blob_path: str) -> dict | list | None:
        """Download a JSON blob and return as Python object."""
        try:
            blob_client = self.client.get_blob_client(
                container=container, blob=blob_path)
            data = json.loads(blob_client.download_blob().readall())
            logger.info(f"Downloaded JSON ← {container}/{blob_path}")
            return data

        except Exception as e:
            logger.error(f"Failed to download {blob_path}: {e}")
            return None

    def blob_exists(self, container: str, blob_path: str) -> bool:
        """
        Check if a blob already exists — used for idempotency.
        If today's file already exists, skip re-ingesting it.
        """
        try:
            blob_client = self.client.get_blob_client(
                container=container, blob=blob_path)
            blob_client.get_blob_properties()
            return True
        except:
            return False

    def list_blobs(self, container: str, prefix: str = "") -> list:
        """List blobs in a container with optional prefix filter."""
        try:
            container_client = self.client.get_container_client(
                container=container)
            blobs = [b.name for b in container_client.list_blobs(
                name_starts_with=prefix)]
            logger.info(f"Listed {len(blobs)} blobs in {container}/{prefix}")
            return blobs
        except Exception as e:
            logger.error(f"Failed to list blobs: {e}")
            return []
