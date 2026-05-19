# ================================================================
# ingest_statsbomb.py — StatsBomb Open Data Ingestion
# Source  : StatsBomb GitHub (raw JSON) — no API key needed
# Target  : Azure ADLS Gen2 → bronze/statsbomb/
# ================================================================

import time
import requests
from datetime import datetime

from utils.azure_client import AzureStorageClient
from utils.config import (
    AZURE_BRONZE_CONTAINER,
    BRONZE_STATSBOMB_PATH,
    validate_config,
)
from utils.logger import get_logger

logger = get_logger(__name__)

STATSBOMB_BASE_URL = (
    "https://raw.githubusercontent.com/"
    "statsbomb/open-data/master/data"
)
UCL_COMPETITION_ID = 16    # Champions League ID in StatsBomb data


# Helper Function
def _fetch_json(url: str) -> dict | list | None:
    """
    Fetch a JSON file from a URL.
    Private helper — prefixed with _ to signal internal use only.
    Returns parsed JSON or None on failure.
    """
    try:
        logger.info(f"Fetching: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error {response.status_code}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {e}")
        return None


def ingest_statsbomb_data() -> bool:
    """
    Ingest StatsBomb Open Data for UCL into Azure ADLS Gen2 Bronze.

    Workflow:
        1. Fetch competitions.json — discover valid UCL season IDs
        2. Upload competitions index to bronze/statsbomb/
        3. For each UCL season found — fetch and upload match list

    Returns:
        True  if competitions index AND all match files succeeded
        False if competitions index failed (cannot proceed without it)

    Note:
        If individual season match files fail, we log the failure
        but still return True for seasons that succeeded.
        The competitions index is the critical dependency.
    """
    logger.info("=" * 60)
    logger.info("Starting StatsBomb Open Data ingestion")
    logger.info(
        f"Source : StatsBomb GitHub (competition_id={UCL_COMPETITION_ID})")
    logger.info(f"Target : {AZURE_BRONZE_CONTAINER}/{BRONZE_STATSBOMB_PATH}")
    logger.info("=" * 60)

    az = AzureStorageClient()

    competitions_blob = f"{BRONZE_STATSBOMB_PATH}competitions.json"

    if az.blob_exists(AZURE_BRONZE_CONTAINER, competitions_blob):
        # Already uploaded — read from Azure instead of hitting GitHub
        logger.info("Competitions index already in Azure — reading from Bronze")
        raw_competitions = az.download_json(
            container=AZURE_BRONZE_CONTAINER,
            blob_path=competitions_blob,
        )
        # Handle both our wrapped format and raw list
        if isinstance(raw_competitions, dict):
            all_competitions = raw_competitions.get("all_competitions", [])
        else:
            all_competitions = raw_competitions or []
    else:
        # Fetch fresh from StatsBomb GitHub
        competitions_url = f"{STATSBOMB_BASE_URL}/competitions.json"
        all_competitions = _fetch_json(competitions_url)

        if not all_competitions:
            logger.error("Failed to fetch competitions.json — cannot proceed")
            return False

        # Upload raw competitions to Bronze
        competitions_payload = {
            "all_competitions": all_competitions,
            "_ingestion_metadata": {
                "ingested_at": datetime.now().isoformat(),
                "ingested_by": "ingest_statsbomb.py",
                "source": "StatsBomb Open Data (GitHub)",
                "endpoint": f"{STATSBOMB_BASE_URL}/competitions.json",
                "layer": "bronze",
                "competition_count": len(all_competitions),
            },
        }
        uploaded = az.upload_json(
            data=competitions_payload,
            container=AZURE_BRONZE_CONTAINER,
            blob_path=competitions_blob,
        )
        if not uploaded:
            logger.error("Failed to upload competitions index to Azure")
            return False

        logger.info(
            f"Competitions index uploaded -> {competitions_blob} "
            f"({len(all_competitions)} total competitions)"
        )

    # ── Step 2: Filter to UCL seasons ─────────────────────────
    ucl_seasons = [
        c for c in all_competitions
        if c.get("competition_id") == UCL_COMPETITION_ID
    ]

    if not ucl_seasons:
        logger.error(
            f"No UCL seasons found in competitions data "
            f"(competition_id={UCL_COMPETITION_ID})"
        )
        return False

    logger.info(
        f"Found {len(ucl_seasons)} UCL seasons in StatsBomb Open Data:")
    for s in ucl_seasons:
        logger.info(
            f"  season_id={s['season_id']} | {s['season_name']}"
        )

    # ── Step 3: Ingest match list for each UCL season ─────────
    # Each season gets its own blob — idempotent per season
    results = {}

    for season in ucl_seasons:
        season_id = season["season_id"]
        season_name = season["season_name"]

        blob_path = (
            f"{BRONZE_STATSBOMB_PATH}"
            f"matches/ucl_season{season_id}_matches.json"
        )

        # Idempotency — skip if this season already uploaded
        if az.blob_exists(AZURE_BRONZE_CONTAINER, blob_path):
            logger.info(
                f"Matches already exist — skipping: "
                f"{season_name} (season_id={season_id})"
            )
            results[season_name] = True
            continue

        # Fetch match list from StatsBomb GitHub
        matches_url = (
            f"{STATSBOMB_BASE_URL}/matches/"
            f"{UCL_COMPETITION_ID}/{season_id}.json"
        )
        matches = _fetch_json(matches_url)

        if not matches:
            logger.error(
                f"No match data for UCL {season_name} "
                f"(season_id={season_id}) — URL: {matches_url}"
            )
            results[season_name] = False
            time.sleep(2)
            continue

        match_count = len(matches)

        # Add ingestion metadata — same watermark pattern as all scripts
        matches_payload = {
            "matches": matches,
            "_ingestion_metadata": {
                "ingested_at": datetime.now().isoformat(),
                "ingested_by": "ingest_statsbomb.py",
                "source": "StatsBomb Open Data (GitHub)",
                "endpoint": matches_url,
                "competition_id": UCL_COMPETITION_ID,
                "season_id": season_id,
                "season_name": season_name,
                "match_count": match_count,
                "layer": "bronze",
            },
        }

        success = az.upload_json(
            data=matches_payload,
            container=AZURE_BRONZE_CONTAINER,
            blob_path=blob_path,
        )
        results[season_name] = success

        if success:
            logger.info(
                f"Matches uploaded | "
                f"season={season_name} | "
                f"count={match_count} | "
                f"path={blob_path}"
            )
        else:
            logger.error(
                f"Upload failed for season {season_name}"
            )

        # Polite pause between GitHub requests
        time.sleep(2)

    # ── Final summary — same style as all ingestion scripts ───
    logger.info("=" * 60)
    logger.info("StatsBomb ingestion summary:")
    for season_name, ok in results.items():
        status = "SUCCESS" if ok else "FAILED"
        logger.info(f"  {season_name} : {status}")
    logger.info("=" * 60)

    overall = all(results.values()) if results else False

    if overall:
        logger.info(
            f"StatsBomb ingestion complete | "
            f"{len(results)} seasons processed"
        )
    else:
        logger.error("StatsBomb ingestion completed with failures")

    return overall


if __name__ == "__main__":
    validate_config()
    result = ingest_statsbomb_data()
    print(f"\nIngestion result: {'SUCCESS' if result else 'FAILED'}")
