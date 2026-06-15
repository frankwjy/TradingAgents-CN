"""
Configuration change event bus.

Provides a lightweight publish/subscribe mechanism so that config writes
(e.g. ConfigService.save_system_config) can notify readers
(e.g. ConfigProvider) to invalidate their caches immediately,
instead of waiting for TTL expiry.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


class ConfigEventBus:
    """Simple synchronous pub/sub for configuration change events."""

    def __init__(self) -> None:
        self._listeners: dict[str, Callable] = {}

    def subscribe(self, callback: Callable) -> str:
        """Register a listener. Returns a token for later unsubscribe."""
        token = uuid.uuid4().hex
        self._listeners[token] = callback
        return token

    def unsubscribe(self, token: str) -> None:
        """Remove a listener by its token."""
        self._listeners.pop(token, None)

    def notify(self, config: Any) -> None:
        """Notify all listeners of a config change. Exceptions are logged but do not propagate."""
        for token, callback in list(self._listeners.items()):
            try:
                callback(config)
            except Exception:
                logger.warning("Config event listener %s raised an exception", token, exc_info=True)


# Module-level singleton
config_event_bus = ConfigEventBus()
