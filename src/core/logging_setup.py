import logging
import sys
import os
import re
from src.core.config import config

class RedactingFilter(logging.Filter):
    """
    A logging filter that redacts sensitive values from log messages and arguments.
    It looks up the values of specified keys in environment variables and replaces
    them with '[REDACTED]' in any log record.
    """
    def __init__(self, sensitive_keys: list[str]):
        super().__init__()
        self.patterns = []
        for key in sensitive_keys:
            val = os.getenv(key)
            if val:
                # Escape the value for regex and add to patterns
                self.patterns.append(re.compile(re.escape(val)))

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern in self.patterns:
                record.msg = pattern.sub("[REDACTED]", record.msg)
        
        if record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern in self.patterns:
                        arg = pattern.sub("[REDACTED]", arg)
                    new_args.append(arg)
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)
        return True

def setup_logging():
    """
    Configures the global logging settings for the application.
    The log level can be set via the 'LOG_LEVEL' environment variable.
    Sensitive keys to redact are loaded from 'SENSITIVE_KEYS'.
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
    
    # Get sensitive keys from config (comma-separated list)
    sensitive_keys_str = config.get_str("SENSITIVE_KEYS", "HF_TOKEN")
    sensitive_keys = [k.strip() for k in sensitive_keys_str.split(",") if k.strip()]
    redacting_filter = RedactingFilter(sensitive_keys)

    # Configure the root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Add filter to all handlers of the root logger
    root = logging.getLogger()
    for handler in root.handlers:
        handler.addFilter(redacting_filter)
    
    logging.info(f"Logging initialized with level: {logging.getLevelName(level)}")

if __name__ == "__main__":
    # Test the setup
    setup_logging()
    # Simulate a secret in environment
    os.environ["HF_TOKEN"] = "super-secret-token"
    # Re-initialize filter with updated env for testing purposes if needed, 
    # but here we just test what was initialized.
    # In a real test, you'd set the env before setup_logging.
    
    logging.debug("This is a debug message")
    logging.info("This is an info message")
    logging.warning("This is a warning message")
    logging.error("This is an error message")
    logging.critical("This is a critical message")
    logging.info("Testing redaction with HF_TOKEN=super-secret-token")
