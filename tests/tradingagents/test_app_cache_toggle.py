import os
import types
import builtins
import pandas as pd
import pytest

from typing import Any, Dict, Optional


class DummyDBManager:
    def __init__(self, available: bool = True):
        self._available = available

    def is_mongodb_available(self) -> bool:
        return self._available

    def get_mongodb_client(self):
        return object()


@pytest.fixture(autouse=True)
def clear_env_and_modules(monkeypatch):
    # Ensure env var is cleared by default for each test
    old = dict(os.environ)
    for k in list(os.environ.keys()):
        if k in ("TA_USE_APP_CACHE",):
            monkeypatch.delenv(k, raising=False)
    yield
    # Restore env
    os.environ.clear()
    os.environ.update(old)


def test_basics_prefers_app_cache_when_enabled(monkeypatch):
    os.environ["TA_USE_APP_CACHE"] = "true"

    # Ensure API branch is reachable in case of fallback
    import tradingagents.dataflows.stock_data_service as sds_mod
    monkeypatch.setattr(sds_mod, "ENHANCED_FETCHER_AVAILABLE", True, raising=False)

    from tradingagents.dataflows.stock_data_service import StockDataService

    svc = StockDataService()
    # Inject dummy db_manager
    monkeypatch.setattr(svc, "db_manager", DummyDBManager(True))

    called = {"api": False}

    def fake_from_mongo(stock_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return {"code": stock_code or "000001", "name": "平安银行", "source": "mongo"}

    def fake_from_api(stock_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        called["api"] = True
        return {"code": stock_code or "000001", "name": "平安银行", "source": "api"}

    monkeypatch.setattr(svc, "_get_from_mongodb", fake_from_mongo)
    monkeypatch.setattr(svc, "_get_from_enhanced_fetcher", fake_from_api)

    res = svc.get_stock_basic_info("000001")
    assert isinstance(res, dict)
    assert res.get("source") == "mongo"
    assert called["api"] is False  # API should not be called when cache hits


def test_basics_fallback_to_api_when_cache_miss(monkeypatch):
    os.environ["TA_USE_APP_CACHE"] = "true"

    # Ensure API branch enabled
    import tradingagents.dataflows.stock_data_service as sds_mod
    monkeypatch.setattr(sds_mod, "ENHANCED_FETCHER_AVAILABLE", True, raising=False)

    from tradingagents.dataflows.stock_data_service import StockDataService

    svc = StockDataService()
    monkeypatch.setattr(svc, "db_manager", DummyDBManager(True))

    called = {"api": False}

    def miss_from_mongo(stock_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return None

    def fake_from_api(stock_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        called["api"] = True
        return {"code": stock_code or "000001", "name": "平安银行", "source": "api"}

    monkeypatch.setattr(svc, "_get_from_mongodb", miss_from_mongo)
    monkeypatch.setattr(svc, "_get_from_enhanced_fetcher", fake_from_api)
    # avoid cache-to-mongo side effect raising inside try
    monkeypatch.setattr(svc, "_cache_to_mongodb", lambda data: True)

    res = svc.get_stock_basic_info("000001")
    assert isinstance(res, dict)
    assert res.get("source") == "api"
    assert called["api"] is True


def test_basics_direct_first_when_disabled(monkeypatch):
    os.environ["TA_USE_APP_CACHE"] = "false"

    # Ensure API branch enabled
    import tradingagents.dataflows.stock_data_service as sds_mod
    monkeypatch.setattr(sds_mod, "ENHANCED_FETCHER_AVAILABLE", True, raising=False)

    from tradingagents.dataflows.stock_data_service import StockDataService

    svc = StockDataService()
    # When TA_USE_APP_CACHE is false, MongoDB should not be available
    monkeypatch.setattr(svc, "db_manager", DummyDBManager(False))

    order = []

    def fake_from_api(stock_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        order.append("api")
        return {"code": stock_code or "000001", "name": "平安银行", "source": "api"}

    def fake_from_mongo(stock_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        order.append("mongo")
        return {"code": stock_code or "000001", "name": "平安银行", "source": "mongo"}

    monkeypatch.setattr(svc, "_get_from_enhanced_fetcher", fake_from_api)
    monkeypatch.setattr(svc, "_get_from_mongodb", fake_from_mongo)
    # avoid cache-to-mongo side effect raising inside try
    monkeypatch.setattr(svc, "_cache_to_mongodb", lambda data: True)

    res = svc.get_stock_basic_info("000001")
    assert isinstance(res, dict)
    assert res.get("source") == "api"
    assert order[0] == "api"


@pytest.mark.skip(reason="app_cache_adapter module no longer exists")
def test_realtime_quotes_prefers_app_market_quotes(monkeypatch):
    pass

