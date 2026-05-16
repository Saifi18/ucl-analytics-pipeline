# ================================================================
# ingest_teams.py — UCL Teams Ingestion
# Source  : football-data.org API → /competitions/CL/teams
# Target  : Azure ADLS Gen2 → bronze/teams/
# ================================================================

from datetime import datetime
from utils.config import validate_config, BRONZE_TEAMS_PATH, AZURE_BRONZE_CONTAINER
from utils.azure_client import AzureStorageClient
from ingestion.api_client import FootballAPIClient
from utils.logger import get_logger

logger = get_logger(__name__)


def ingest_ucl_teams(season: int = 2024) -> bool:
    """Ingest all UCL team metadata for a given season. Writes raw JSON to Azure ADLS Gen2 Bronze container
    Args: season : UCL season year (default 2024 = 2024/25 season)"""

    today = datetime.now().strftime("%Y-%m-%d")
    blob_path = f"{BRONZE_TEAMS_PATH}{today}_ucl_teams_season_{season}.json"

    logger.info("=" * 60)
    logger.info("Starting UCL team ingestion")
    logger.info(f"Season   : {season}")
    logger.info(f"Target   : {AZURE_BRONZE_CONTAINER}/{blob_path}")
    logger.info("=" * 60)

    # Idempotency check

    az = AzureStorageClient()

    if az.blob_exists(container=AZURE_BRONZE_CONTAINER, blob_path=blob_path):
        logger.info(f"File already exists — skipping ingestion: {blob_path}")
        return True

    # Fetch Football API data

    api = FootballAPIClient()
    data = api.get_ucl_teams(season=season)

    if not data:
        logger.error("API returned no data — check API key and network")
        return False

    # Validating API response structure
    teams = data.get("teams", [])
    if not teams:
        logger.warning(
            "API returned empty teams list — writing anyway for audit trail")

    team_count = len(teams)
    logger.info(f"API returned {team_count} teams")

    # Add ingestion metadata
    data["_ingestion_metadata"] = {
        "ingested_at": datetime.now().isoformat(),
        "ingested_by": "ingest_teams.py",
        "season": season,
        "source": "football-data.org/v4",
        "endpoint": f"competitions/CL/teams?season={season}",
        "layer": "bronze",
        "team_count": team_count,
    }

    success = az.upload_json(
        data=data, container=AZURE_BRONZE_CONTAINER, blob_path=blob_path)

    if not success:
        logger.error(
            "Failed to upload teams data to Azure — check connection and permissions")
        return False

    return success


if __name__ == "__main__":
    validate_config()
    result = ingest_ucl_teams(season=2024)
    print(f"\nIngestion result: {'✅ SUCCESS' if result else '❌ FAILED'}")
