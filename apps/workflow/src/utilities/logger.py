import sys
import logging


def setup_logger(level=logging.INFO):
    """
    Setup for the main logger.
    """
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s %(module)s %(processName)s - %(message)s', datefmt="%Y-%m-%dT%H:%M:%S%z")
    logger = logging.getLogger()
    logger.setLevel(level)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
