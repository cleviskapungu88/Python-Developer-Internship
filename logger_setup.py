"""
STEP 1 — logger_setup.py
Sets up a dual logger: writes to a rotating log file AND prints to the console.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def get_logger(log_file: str, name: str = "AutoOrganizer") -> logging.Logger:
    """
    Create and return a logger that:
      • Writes DEBUG+ messages to a rotating log file (max 1 MB, 3 backups)
      • Writes INFO+  messages to the console in colour-friendly format

    Args:
        log_file: Path to the .log file (parent dirs are created automatically).
        name:     Logger name (shows up in every log line).
    """
    # ── Ensure log directory exists ────────────────────────────────────────────
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)          # capture everything at root level

    # ── Shared formatter ───────────────────────────────────────────────────────
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── File handler (rotating, so the log never grows huge) ──────────────────
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        fh = RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    # ── Console handler ────────────────────────────────────────────────────────
    if not any(isinstance(h, logging.StreamHandler) and
               not isinstance(h, RotatingFileHandler)
               for h in logger.handlers):
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    return logger
