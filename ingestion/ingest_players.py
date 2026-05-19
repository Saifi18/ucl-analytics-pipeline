# ================================================================
# ingest_players.py — UCL Top Scorers + Player Ingestion
# Source  : football-data.org API → /competitions/CL/scorers
# Target  : Azure ADLS Gen2 → bronze/players/
# ================================================================

from datetime import datetime
from utils.config import validate_config, AZURE_BRONZE_CONTAINER, BRONZE_PLAYERS_PATH
from utils.azure_client import AzureStorageClient
from ingestion.api_client import FootballAPIClient
from utils.logger import get_logger

logger = get_logger(__name__)


def ingest_ucl_scorers(season: int = 2024, limit: int = 50) -> bool:
    """
    Ingest UCL top scorers for a given season.
    Writes raw JSON to Azure ADLS Gen2 Bronze container.
    Args: season : UCL season year (default 2024) limit  : Number of top scorers to retrieve (max 50 on free tier)
    """

    today = datetime.now().strftime("%Y-%m-%d")
    blob_path = f"{BRONZE_PLAYERS_PATH}{today}_ucl_top_scorers_season_{season}.json"

    logger.info("=" * 60)
    logger.info("Starting UCL top scorers ingestion")
    logger.info(f"Season   : {season}")
    logger.info(f"Limit    : top {limit} scorers")
    logger.info(f"Target   : {AZURE_BRONZE_CONTAINER}/{blob_path}")
    logger.info("=" * 60)

    # Idempotency check

    az = AzureStorageClient()

    if az.blob_exists(AZURE_BRONZE_CONTAINER, blob_path):
        logger.info(f"File already exists — skipping ingestion: {blob_path}")
        return True

    api = FootballAPIClient()
    data = api.get_ucl_top_scorers(season=season)

    if not data:
        logger.error("API returned no data — aborting")
        return False

    # Validate log response
    scorers = data.get("scorers", [])
    scorer_count = len(scorers)
    logger.info(f"API returned {scorer_count} scorers")

    # Lof 3 top scorers for traceability
    logger.info("Top 3 scorers:")

    for i, scorer_entry in enumerate(scorers[:3], start=1):
        player = scorer_entry.get("player", {})
        name = player.get("name", "Unknown")
        goals = scorer_entry.get("goals", 0)
        team = scorer_entry.get("team", {}).get("name", "Unknown")
        logger.info(f"  {i}. {name} ({team}) — {goals} goals")

    # Add ingestion metadata for traceability

    data["ingestion_metadata"] = {
        "ingested_at": datetime.now().isoformat(),
        "ingested_by": "ingest_players.py",
        "season": season,
        "source": "football-data.org/v4",
        "endpoint": f"competitions/CL/scorers?season={season}",
        "layer": "bronze",
        "scorer_count": scorer_count,
        "limit_applied": limit,
    }

    success = az.upload_json(
        container=AZURE_BRONZE_CONTAINER, blob_path=blob_path, data=data)

    if success:
        logger.info(f"   Players ingestion complete")
        logger.info(f"   Scorers written : {scorer_count}")
        logger.info(f"   Blob path       : {blob_path}")
    else:
        logger.error(" Upload to Azure failed")

    return success


if __name__ == "__main__":
    validate_config()
    result = ingest_ucl_scorers(season=2024)
    print(f"\nIngestion result: {'SUCCESS' if result else ' FAILED'}")
