from logging.handlers import RotatingFileHandler
import logging

def setup_logger(name: str, log_file: str, level=logging.INFO):
    """Creates and returns a logger with a specific file"""
    handler = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent duplicate logs
    if not logger.handlers:
        logger.addHandler(handler)
        logger.propagate = False

    return logger