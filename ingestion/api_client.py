# ================================================================
# api_client.py — football-data.org API wrapper
# Handles: auth headers, rate limiting, retries, error handling
# ================================================================


import requests
import time
from utils.config import FOOTBALL_API_KEY, FOOTBALL_API_BASE_URL, API_RATE_LIMIT_PAUSE, UCL_COMPETITION_CODE
from utils.logger import get_logger

logger = get_logger(__name__)


class FootballAPIClient:

    """Wrapper for football-data.org REST API v4.Free tier: 10 requests/min. Always respect rate limits."""

    def __init__(self):
        self.headers = {"X-Auth-Token": FOOTBALL_API_KEY}
        self.base_url = FOOTBALL_API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        logger.info("FootballAPIClient initialised")

    def _get(self, endpoint: str, params: dict = None) -> dict | None:
        """Internal GET method with rate limiting and retry logic.
        Prefixed with _ to signal "internal use only" convention. 
        All public methods call this — never call requests directly.
        """
        url = f"{self.base_url}/{endpoint}"
        max_retries = 3

        for attempt in range(max_retries):
            try:
                logger.info(f"GET {url} | params={params}")

                response = self.session.get(url, params=params, timeout=30)

                # 429 = Too Many Requests
                if response.status_code == 429:
                    wait_time = 60  # seconds
                    logger.warning(
                        f"Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()

                # Pause to respect rate limits
                time.sleep(API_RATE_LIMIT_PAUSE)

                return response.json()
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error on attempt {attempt + 1}: {e}")

                if attempt == max_retries - 1:
                    return None

                time.sleep(10)  # Wait before retrying

        return None

    def get_ucl_matches(self, season: int = 2024) -> dict | None:
        """Get all UCL matches for a given season."""
        logger.info(f"Fetching UCL matches for season {season}")

        return self._get(f"competitions/{UCL_COMPETITION_CODE}/matches", params={"season": season})

    def get_ucl_standings(self, season: int = 2024) -> dict | None:
        """Get UCL group stage standings."""
        logger.info(f"Fetching UCL standings for season {season}")

        return self._get(
            f"competitions/{UCL_COMPETITION_CODE}/standings",
            params={"season": season}
        )

    def get_ucl_top_scorers(self, season: int = 2024) -> dict | None:
        """Get UCL top scorers leaderboard."""
        logger.info(f"Fetching UCL top scorers for season {season}")
        return self._get(
            f"competitions/{UCL_COMPETITION_CODE}/scorers",
            params={"season": season}
        )

    def get_ucl_teams(self, season: int = 2024) -> dict | None:
        """Get all teams in the UCL competition."""
        logger.info(f"Fetching UCL teams for season {season}")
        return self._get(
            f"competitions/{UCL_COMPETITION_CODE}/teams",
            params={"season": season}
        )
