import logging
import sys
from src.core.config import config

def setup_logging():
    """
    Configures the global logging settings for the application.
    The log level can be set via the 'LOG_LEVEL' environment variable.
    """
    log_level_str = config.get_str("LOG_LEVEL", "INFO").upper()
    
    # Map string levels to logging constants
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    level = levels.get(log_level_str, logging.INFO)

    # Configure the root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info(f"Logging initialized with level: {logging.getLevelName(level)}")

if __name__ == "__main__":
    # Test the setup
    setup_logging()
    logging.debug("This is a debug message")
    logging.info("This is an info message")
    logging.warning("This is a warning message")
    logging.error("This is an error message")
    logging.critical("This is a critical message")
