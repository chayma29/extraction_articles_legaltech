# src/utils.py
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def ensure_dir(path: Path) -> Path:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Directory ensured: {path}")
    return path