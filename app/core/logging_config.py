"""
AegisClaim AI - Structured Logging Configuration
"""
import logging
import sys
from datetime import datetime


class AegisFormatter(logging.Formatter):
    """Custom formatter with color and structured output."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.colored_level = f"{color}{record.levelname:8s}{self.RESET}"
        record.timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        return super().format(record)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure application logging."""
    logger = logging.getLogger("aegisclaim")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = AegisFormatter(
            '%(timestamp)s | %(colored_level)s | %(name)s.%(funcName)s | %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


# Module-level logger
logger = setup_logging()
