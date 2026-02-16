"""Logging configuration for the trading bot.

Sets up dual logging: a rotating file handler for persistent logs and a
console handler for real-time feedback.  All API requests, responses, and
errors are captured at the appropriate level.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

# Maximum log file size: 5 MB, keep 3 backups
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.DEBUG) -> logging.Logger:
    """Initialise and return the root application logger.

    Parameters
    ----------
    level : int
        Logging level for the file handler.  The console handler always
        uses INFO to avoid flooding the terminal.

    Returns
    -------
    logging.Logger
        Configured root logger for the ``bot`` package.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("bot")
    logger.setLevel(level)

    # Prevent duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # --- Rotating file handler (DEBUG and above) ---
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # --- Console handler (INFO and above) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
