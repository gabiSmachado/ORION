import logging
import sys
from typing import Optional

DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def get_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    console_level: Optional[int] = None,
    fmt: str = DEFAULT_FORMAT,
    propagate: bool = False,
):
    """Return a configured logger.

    Ensures we don't attach duplicate handlers if called multiple times.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate

    formatter = logging.Formatter(fmt)

    # Add/ensure file handler
    if log_file:
        if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) and h.baseFilename.endswith(log_file) for h in logger.handlers):
            fh = logging.FileHandler(log_file)
            fh.setLevel(level)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

    # Add/ensure console handler
    if console_level is None:
        console_level = level
    if not any(isinstance(h, logging.StreamHandler) and getattr(h, 'stream', None) is sys.stdout for h in logger.handlers):
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(console_level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger