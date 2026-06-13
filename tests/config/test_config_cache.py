"""
Tests for configuration caching, auto-invalidation, and update notifications.

These tests verify:
1. ConfigService caches get_system_config() results with TTL
2. Cache is invalidated when save_system_config() is called
3. Config change notification system notifies listeners
4. ConfigProvider auto-invalidates on config changes
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.config import SystemConfig


def _make_test_config(version=1, settings=None):
    """Create a minimal SystemConfig for testing."""
    return SystemConfig(
        config_name="test",
        config_type="system",
        llm_configs=[],
        data_source_configs=[],
        database_configs=[],
        system_settings=settings or {"test_key": "test_value"},
        version=version,
        is_active=True,
    )


def _make_mock_db(find_one_return=None):
    """Create a mock MongoDB with AsyncMock collection methods."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=find_one_return)
    mock_collection.update_many = AsyncMock(return_value=MagicMock(modified_count=0))
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="abc123"))
    mock_db.system_configs = mock_collection
    return mock_db, mock_collection


# ===== Config Change Event Tests =====


class TestConfigChangeEvent:
    """Test the config change notification system."""

    def test_subscribe_and_notify(self):
        from app.services.config_events import ConfigEventBus

        bus = ConfigEventBus()
        calls = []

        def listener(config):
            calls.append(config)

        bus.subscribe(listener)
        bus.notify(_make_test_config())

        assert len(calls) == 1
        assert calls[0].config_name == "test"

    def test_multiple_listeners(self):
        from app.services.config_events import ConfigEventBus

        bus = ConfigEventBus()
        calls_a = []
        calls_b = []

        bus.subscribe(lambda c: calls_a.append(c))
        bus.subscribe(lambda c: calls_b.append(c))
        bus.notify(_make_test_config())

        assert len(calls_a) == 1
        assert len(calls_b) == 1

    def test_unsubscribe(self):
        from app.services.config_events import ConfigEventBus

        bus = ConfigEventBus()
        calls = []

        token = bus.subscribe(lambda c: calls.append(c))
        bus.unsubscribe(token)
        bus.notify(_make_test_config())

        assert len(calls) == 0

    def test_notify_with_no_listeners(self):
        from app.services.config_events import ConfigEventBus

        bus = ConfigEventBus()
        bus.notify(_make_test_config())  # Should not raise

    def test_listener_exception_does_not_block_others(self):
        from app.services.config_events import ConfigEventBus

        bus = ConfigEventBus()
        calls = []

        bus.subscribe(lambda c: 1 / 0)  # Will raise
        bus.subscribe(lambda c: calls.append(c))
        bus.notify(_make_test_config())

        assert len(calls) == 1


# ===== ConfigService Caching Tests =====


class TestConfigServiceCache:
    """Test ConfigService.get_system_config() caching."""

    def setup_method(self):
        from app.services.config_service import config_service
        config_service._cache_config = None
        config_service._cache_time = None
        config_service._cache_ttl_seconds = 30

    def test_get_system_config_returns_cached_result(self):
        """Repeated calls within TTL should return cached result without DB hit."""
        from app.services.config_service import config_service

        test_config = _make_test_config(version=1)
        mock_db, mock_collection = _make_mock_db(test_config.model_dump(by_alias=True))
        config_service.db = mock_db

        async def run_test():
            # First call - should hit DB
            result1 = await config_service.get_system_config()
            call_count_1 = mock_collection.find_one.call_count

            # Second call within TTL - should use cache
            result2 = await config_service.get_system_config()
            call_count_2 = mock_collection.find_one.call_count

            assert result1 is not None
            assert result2 is not None
            assert call_count_2 == call_count_1  # No additional DB call

        asyncio.run(run_test())

    def test_cache_expires_after_ttl(self):
        """After TTL expires, should hit DB again."""
        from app.services.config_service import config_service

        test_config = _make_test_config(version=1)
        mock_db, mock_collection = _make_mock_db(test_config.model_dump(by_alias=True))
        config_service.db = mock_db
        config_service._cache_ttl_seconds = 0  # Immediate expiry

        async def run_test():
            await config_service.get_system_config()
            call_count_1 = mock_collection.find_one.call_count

            # With TTL=0, next call should hit DB
            await config_service.get_system_config()
            call_count_2 = mock_collection.find_one.call_count

            assert call_count_2 > call_count_1

        asyncio.run(run_test())

    def test_save_system_config_invalidates_cache(self):
        """After save, cache should be invalidated so next get fetches fresh data."""
        from app.services.config_service import config_service

        test_config = _make_test_config(version=1)
        mock_db, mock_collection = _make_mock_db(test_config.model_dump(by_alias=True))
        config_service.db = mock_db

        async def run_test():
            # Prime the cache
            await config_service.get_system_config()
            assert config_service._cache_config is not None

            # Save should invalidate cache
            await config_service.save_system_config(test_config)
            assert config_service._cache_config is None

        asyncio.run(run_test())

    def test_invalidate_cache_clears_cache(self):
        """Manual invalidation should clear the cache."""
        from app.services.config_service import config_service

        config_service._cache_config = _make_test_config()
        config_service._cache_time = datetime.now(timezone.utc)

        config_service.invalidate_cache()

        assert config_service._cache_config is None
        assert config_service._cache_time is None


# ===== ConfigProvider Auto-invalidation Tests =====


class TestConfigProviderAutoInvalidation:
    """Test that ConfigProvider auto-invalidates when config changes."""

    def setup_method(self):
        from app.services.config_provider import provider
        provider._cache_settings = None
        provider._cache_time = None

    def test_provider_invalidates_on_config_change_event(self):
        """ConfigProvider should auto-invalidate when notified of config change."""
        from app.services.config_provider import provider
        from app.services.config_events import config_event_bus

        # Prime the cache
        provider._cache_settings = {"key": "old_value"}
        provider._cache_time = datetime.now(timezone.utc)

        # Register for events
        provider.register_config_listener()

        # Simulate config change notification
        config_event_bus.notify(_make_test_config())

        # Cache should be invalidated
        assert provider._cache_settings is None
        assert provider._cache_time is None


# ===== Integration: ConfigService notifies on save =====


class TestConfigServiceNotificationIntegration:
    """Test that ConfigService notifies the event bus on save."""

    def setup_method(self):
        from app.services.config_service import config_service
        config_service._cache_config = None
        config_service._cache_time = None

    def test_save_triggers_notification(self):
        """save_system_config should notify all listeners via the event bus."""
        from app.services.config_service import config_service
        from app.services.config_events import config_event_bus

        test_config = _make_test_config(version=1)
        mock_db, mock_collection = _make_mock_db(test_config.model_dump(by_alias=True))
        config_service.db = mock_db

        notifications = []
        config_event_bus.subscribe(lambda c: notifications.append(c))

        async def run_test():
            await config_service.save_system_config(test_config)
            assert len(notifications) == 1
            assert notifications[0].config_name == "test"

        asyncio.run(run_test())
