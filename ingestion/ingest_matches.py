# ================================================================
# ingest_matches.py — UCL Match Ingestion
# Source : football-data.org API
# Target : Azure ADLS Gen2 → bronze container → matches/
# ================================================================

from datetime import datetime
from utils.config import validate_config, BRONZE_MATCHES_PATH, AZURE_BRONZE_CONTAINER
from utils.azure_client import AzureStorageClient
from ingestion.api_client import FootballAPIClient
from utils.logger import get_logger

logger = get_logger(__name__)


def ingest_ucl_matches(season: int = 2024) -> bool:
    """Ingest UCL matches for a given season from football-data.org
        and write raw JSON to Azure ADLS Gen2 Bronze container.
        Idempotent: skips if today's file already exists.
        Returns: True if successful or skipped, False if failed."""

    # Build target blob path
    today = datetime.now().strftime("%Y-%m-%d")
    blob_path = f"{BRONZE_MATCHES_PATH}{today}_ucl_matches_season_{season}.json"

    logger.info(f"Starting UCL match ingestion | season={season}")
    logger.info(f"Target: {AZURE_BRONZE_CONTAINER}/{blob_path}")

    az = AzureStorageClient()

    if az.blob_exists(AZURE_BRONZE_CONTAINER, blob_path):
        logger.info(f"File already exists — skipping: {blob_path}")
        return True

    api = FootballAPIClient()
    data = api.get_ucl_matches(season=season)

    if not data:
        logger.error("API returned no data — aborting ingestion")
        return False

    # Adding metadata for traceability

    data["_ingestion_metadata"] = {
        "ingested_at": datetime.now().isoformat(),
        "season": season,
        "source": "football-data.org",
        "layer": "bronze",
        "match_count": len(data.get("matches", [])),
    }

    success = az.upload_json(
        data=data,
        container=AZURE_BRONZE_CONTAINER,
        blob_path=blob_path,
    )

    if success:
        match_count = len(data.get("matches", []))

        logger.info(
            f"✅ Ingestion complete | "
            f"{match_count} matches → {blob_path}"
        )

    else:
        logger.error("❌ Upload failed — check Azure credentials")

    return success


if __name__ == "__main__":

    # Validate config before running
    validate_config()

    # Run ingestion
    result = ingest_ucl_matches(season=2024)

    print(
        f"Ingestion result: "
        f"{'✅ SUCCESS' if result else '❌ FAILED'}"
    )
