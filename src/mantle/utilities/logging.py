"""Project logger factory."""

from pathlib import Path
import logging


def get_logger(name: str, log_file: str | Path | None = None) -> logging.Logger:
    """Create an idempotent console/file logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        logger.addHandler(stream)
        if log_file is not None:
            target = Path(log_file)
            target.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(target, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    return logger

