import logging
import sys
import os
import re
import structlog
from typing import Optional
from src.core.config import ConfigManager, config

class RedactingProcessor:
    """
    A structlog processor that redacts sensitive values from log messages and arguments.
    """
    def __init__(self, sensitive_keys: list[str]):
        super().__init__()
        self.patterns = []
        for key in sensitive_keys:
            val = os.getenv(key)
            if val:
                # Escape the value for regex and add to patterns
                self.patterns.append(re.compile(re.escape(val)))

    def __call__(self, logger, method_name, event_dict):
        for key, value in event_dict.items():
            if isinstance(value, str):
                for pattern in self.patterns:
                    if pattern.search(value):
                        event_dict[key] = pattern.sub("[REDACTED]", value)
            elif isinstance(value, (dict, list)):
                # For complex types, we might need a more recursive approach if they contain strings
                # but for now let's keep it simple and just redact the top level or skip
                pass
        return event_dict

def setup_logging(cfg: Optional[ConfigManager] = None):
    """
    Configures the global logging settings for the application using structlog.
    """
    if cfg is None:
        cfg = config

    log_level_str = cfg.get_str("LOG_LEVEL", "INFO").upper()
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    level = levels.get(log_level_str, logging.INFO)

    sensitive_keys_str = cfg.get_str("SENSITIVE_KEYS", "HF_TOKEN")
    sensitive_keys = [k.strip() for k in sensitive_keys_str.split(",") if k.strip()]
    redacting_processor = RedactingProcessor(sensitive_keys)

    # Shared processors for both structlog and standard logging (if we use structlog to wrap it)
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        redacting_processor,
    ]

    # If we want JSON output in production
    if cfg.get_bool("PRODUCTION", False):
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_onFirstUse=True,
    )

    # Also configure the standard logging library to use structlog's output if possible, 
    # or just ensure it's configured so that other libraries using it also work.
    logging.basicConfig(
        level=level,
        format="%(message)s", # structlog will handle the formatting
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    logging.info(f"Logging initialized with level: {logging.getLevelName(level)}")

if __name__ == "__main__":
    # Test the setup
    os.environ["HF_TOKEN"] = "super-secret-token"
    setup_logging()
    import structlog
    log = structlog.get_logger()
    log.debug("This is a debug message")
    log.info("This is an info message")
    log.warning("This is a warning message")
    log.error("This is an error message")
    log.critical("This is a critical message")
    log.info("Testing redaction with HF_TOKEN=super-secret-token")
