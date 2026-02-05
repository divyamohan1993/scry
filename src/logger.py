import logging
import os
import sys
from datetime import datetime

try:
    from .config import DEVELOPER_MODE, LOGS_DIR
except ImportError:
    # Fallback if config isn't fully ready or circular import
    DEVELOPER_MODE = False
    # Fallback log dir if config fails
    LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_runtime", "logs")


class SafeStreamHandler(logging.StreamHandler):
    """
    A StreamHandler that gracefully handles Unicode encoding errors.
    On Windows consoles that use cp1252 encoding, emojis and other
    Unicode characters may fail to encode. This handler catches those
    errors and replaces problematic characters with their Unicode escape
    sequences or question marks.
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # Try to write the message normally
            try:
                stream.write(msg + self.terminator)
            except UnicodeEncodeError:
                # Replace unencodable characters with their escape sequences
                safe_msg = msg.encode(stream.encoding or 'utf-8', errors='replace').decode(stream.encoding or 'utf-8', errors='replace')
                stream.write(safe_msg + self.terminator)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


def get_logger(name):
    # Create logs directory if it doesn't exist (handled in config but safe to ensure)
    os.makedirs(LOGS_DIR, exist_ok=True)


    # Generate log filename with timestamp
    log_file = os.path.join(
        LOGS_DIR, f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Clean existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    # File Handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Console Handler - Use SafeStreamHandler to handle Unicode gracefully
    console_handler = SafeStreamHandler(sys.stdout)
    # Set console level based on Developer Mode
    if DEVELOPER_MODE:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.INFO)

    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
