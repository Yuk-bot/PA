import json
import logging
from typing import Dict, Any

class StructuredLogger:
    """
    Structured JSON logger for agent execution logs, state transitions,
    evaluators, and event publications.
    """
    def __init__(self, name: str) -> None:
        self.logger = logging.getLogger(name)

    def info(self, event: str, details: Dict[str, Any]) -> None:
        log_payload = {
            "level": "INFO",
            "event": event,
            **details
        }
        self.logger.info(json.dumps(log_payload))

    def warning(self, event: str, details: Dict[str, Any]) -> None:
        log_payload = {
            "level": "WARNING",
            "event": event,
            **details
        }
        self.logger.warning(json.dumps(log_payload))

    def error(self, event: str, details: Dict[str, Any]) -> None:
        log_payload = {
            "level": "ERROR",
            "event": event,
            **details
        }
        self.logger.error(json.dumps(log_payload))
