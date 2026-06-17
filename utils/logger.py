# ================================================================
# logger.py — Centralised logging setup
# ================================================================

import logging
import os
from datetime import datetime


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger for the given module name.
    Usage: logger = get_logger(__name__)
    """

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Format: timestamp | level | module | message
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        # --- Console handler prints to terminal ---
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # --- File handler writes to logs/ folder ---
        log_dir = "logs"

        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(
            log_dir,
            f"ucl_pipeline_{datetime.now().strftime('%Y%m%d')}.log"
        )

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger


# ── Quick test when run directly ──
if __name__ == "__main__":
    logger = get_logger("test")
    logger.info("Logger is working")
    logger.warning("This is a warning")
    logger.error("This is an error")
