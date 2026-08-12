import logging
import sys
from typing import Any, Dict


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def structured_log(level: str, event: str, **fields: Any) -> None:
    record: Dict[str, Any] = {"event": event, **fields}
    logger = get_logger("genai_agents")
    getattr(logger, level.lower())(str(record))
