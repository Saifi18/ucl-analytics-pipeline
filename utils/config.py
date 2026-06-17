# ================================================================
# config.py — Centralised project configuration
# ================================================================

from dotenv import load_dotenv
import os

load_dotenv()

# --- Azure Configuration ---
AZURE_STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT")
AZURE_STORAGE_KEY = os.getenv("AZURE_STORAGE_KEY")
AZURE_BRONZE_CONTAINER = os.getenv("AZURE_BRONZE_CONTAINER")
AZURE_SILVER_CONTAINER = os.getenv("AZURE_SILVER_CONTAINER")
AZURE_GOLD_CONTAINER = os.getenv("AZURE_GOLD_CONTAINER")

# --- API Configuration ---
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
FOOTBALL_API_BASE_URL = "https://api.football-data.org/v4"
UCL_COMPETITION_CODE = "CL"
API_RATE_LIMIT_PAUSE = 6  # seconds between requests (free tier = 10 req/min)

# --- Bronze folder paths inside Azure containers ---
BRONZE_MATCHES_PATH = "matches/"
BRONZE_TEAMS_PATH = "teams/"
BRONZE_PLAYERS_PATH = "players/"
BRONZE_STATSBOMB_PATH = "statsbomb/"


# --- Validation fail loudly if secrets are missing ---
def validate_config():
    required = {
        "AZURE_STORAGE_ACCOUNT": AZURE_STORAGE_ACCOUNT,
        "AZURE_STORAGE_KEY": AZURE_STORAGE_KEY,
        "FOOTBALL_API_KEY": FOOTBALL_API_KEY,
    }

    missing = [k for k, v in required.items() if not v]

    if missing:
        raise EnvironmentError(
            f"Missing required config keys: {missing}\n"
            f"Add them to your .env file."
        )


if __name__ == "__main__":
    validate_config()
    print("✅ All config values loaded successfully")
