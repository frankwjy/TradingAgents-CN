"""
测试实时PE/PB计算功能
"""

import pytest

from tradingagents.dataflows.realtime_metrics import calculate_realtime_pe_pb, get_pe_pb_with_fallback, validate_pe_pb


def test_validate_pe_pb():
    """测试PE/PB验证"""
    # 正常范围
    assert validate_pe_pb(20.5, 3.2) == True
    assert validate_pe_pb(50, 2.5) == True
    assert validate_pe_pb(-10, 1.5) == True  # 允许负PE（亏损企业）

    # PE异常
    assert validate_pe_pb(1500, 3.2) == False  # PE过大
    assert validate_pe_pb(-150, 3.2) == False  # PE过小

    # PB异常
    assert validate_pe_pb(20.5, 150) == False  # PB过大
    assert validate_pe_pb(20.5, 0.05) == False  # PB过小

    # None值
    assert validate_pe_pb(None, 3.2) == True
    assert validate_pe_pb(20.5, None) == True
    assert validate_pe_pb(None, None) == True


@pytest.mark.integration
def test_calculate_realtime_pe_pb_with_mock_data(monkeypatch):
    """测试实时PE/PB计算（使用mock数据）"""

    # Mock MongoDB数据
    class MockCollection:
        def __init__(self, collection_type=""):
            self.collection_type = collection_type

        def find_one(self, query, **kwargs):
            code = query.get("code")
            if code == "000001":
                if self.collection_type == "market_quotes":
                    # 返回实时行情（含pre_close）
                    return {
                        "code": "000001",
                        "close": 10.5,
                        "pre_close": 10.0,
                        "updated_at": "2025-10-14T10:30:00",
                    }
                elif self.collection_type == "stock_basic_info":
                    # 返回Tushare基础信息（含source和pe_ttm）
                    return {
                        "code": "000001",
                        "source": "tushare",
                        "total_share": 100000,  # 10万万股 = 10亿股
                        "net_profit": 50000,  # 5万万元 = 5亿元
                        "total_hldr_eqy_exc_min_int": 200000,  # 20万万元 = 20亿元
                        "pe_ttm": 21.0,
                    }
                elif self.collection_type == "stock_financial_data":
                    # 返回财务数据（用于PB计算）
                    return {
                        "code": "000001",
                        "total_equity": 2000000000,  # 20亿（元）
                    }
            return None

    class MockDB:
        def __getitem__(self, name):
            return MockCollection(name)

        def __getattr__(self, name):
            return self[name]

    class MockClient:
        def __getitem__(self, name):
            return MockDB()

    # 执行测试
    result = calculate_realtime_pe_pb("000001", MockClient())

    # 验证结果
    assert result is not None
    assert result["price"] == 10.5
    assert result["is_realtime"] == True

    # 验证PE计算：
    # 昨日市值 = 100000万股 * 10.0元 / 10000 = 100亿元
    # TTM净利润 = 100 / 21.0 ≈ 4.76亿元
    # 实时市值 = 10.5 * 100000 / 10000 = 105亿元
    # 动态PE = 105 / 4.76 ≈ 22.05
    assert result["pe"] is not None
    assert result["pe"] > 0

    # 验证PB计算：
    # 净资产 = 20亿元
    # PB = 105 / 20 = 5.25
    assert result["pb"] is not None
    assert result["pb"] > 0


def test_calculate_realtime_pe_pb_missing_data(monkeypatch):
    """测试缺少数据时的处理"""

    class MockCollection:
        def find_one(self, query):
            return None

    class MockDB:
        def __getitem__(self, name):
            return MockCollection()

        def __getattr__(self, name):
            return self[name]

    class MockClient:
        def __getitem__(self, name):
            return MockDB()

    # 执行测试
    result = calculate_realtime_pe_pb("999999", MockClient())

    # 验证结果
    assert result is None


@pytest.mark.integration
def test_get_pe_pb_with_fallback_success(monkeypatch):
    """测试带降级的获取函数（成功场景）"""

    # Mock实时计算成功
    def mock_calculate(symbol, db_client):
        return {
            "pe": 22.5,
            "pb": 3.2,
            "pe_ttm": 23.1,
            "pb_mrq": 3.3,
            "source": "realtime_calculated",
            "is_realtime": True,
            "updated_at": "2025-10-14T10:30:00",
        }

    class MockDB:
        pass

    class MockClient:
        def __getitem__(self, name):
            return MockDB()

    import tradingagents.dataflows.realtime_metrics as metrics_module

    monkeypatch.setattr(metrics_module, "calculate_realtime_pe_pb", mock_calculate)

    # 执行测试
    result = get_pe_pb_with_fallback("000001", MockClient())

    # 验证结果
    assert result["pe"] == 22.5
    assert result["pb"] == 3.2
    assert result["is_realtime"] == True


@pytest.mark.integration
def test_get_pe_pb_with_fallback_to_static(monkeypatch):
    """测试降级到静态数据"""

    # Mock实时计算失败
    def mock_calculate(symbol, db_client):
        return None

    # Mock静态数据获取
    class MockCollection:
        def find_one(self, query):
            return {
                "code": "000001",
                "pe": 20.0,
                "pb": 3.0,
                "pe_ttm": 21.0,
                "pb_mrq": 3.1,
                "updated_at": "2025-10-13T16:00:00",
            }

    class MockDB:
        def __getitem__(self, name):
            return MockCollection()

        def __getattr__(self, name):
            return self[name]

    class MockClient:
        def __getitem__(self, name):
            return MockDB()

    import tradingagents.dataflows.realtime_metrics as metrics_module

    monkeypatch.setattr(metrics_module, "calculate_realtime_pe_pb", mock_calculate)

    # 执行测试
    result = get_pe_pb_with_fallback("000001", MockClient())

    # 验证结果
    assert result["pe"] == 20.0
    assert result["pb"] == 3.0
    assert result["is_realtime"] == False
    assert result["source"] == "daily_basic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
