import sys
import logging


logging.basicConfig(
    format="%(asctime)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


def log_and_raise(exception, message):
    """
    Log the given message as an error, and then raise the exception.

    Args:
        exception: The exception to be raised.
        message (str): The message to be logged before raising the exception.

    Raises:
        exception: The given exception.
    """
    logging.error(message)
    raise exception
