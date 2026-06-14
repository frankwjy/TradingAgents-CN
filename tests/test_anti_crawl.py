"""
反爬虫检测模块测试
"""
import pytest
import time
from unittest.mock import Mock, patch
from tradingagents.dataflows.providers.china.anti_crawl import (
    AntiCrawlDetector,
    AntiCrawlStatus,
    AntiCrawlResult,
)


class TestAntiCrawlDetector:
    """反爬虫检测器测试"""

    def setup_method(self):
        """测试前重置状态"""
        AntiCrawlDetector._request_history.clear()

    def test_detect_normal_response(self):
        """测试正常响应检测"""
        # 模拟一个有数据的DataFrame
        mock_df = Mock()
        mock_df.empty = False
        mock_df.__len__ = Mock(return_value=100)
        mock_df.to_string = Mock(return_value="正常数据内容")

        result = AntiCrawlDetector.detect(mock_df, source="akshare")
        assert result.status == AntiCrawlStatus.NORMAL

    def test_detect_none_response(self):
        """测试None响应检测"""
        result = AntiCrawlDetector.detect(None, source="akshare")
        assert result.status == AntiCrawlStatus.EMPTY_DATA
        assert "None" in result.message

    def test_detect_empty_dataframe(self):
        """测试空DataFrame检测"""
        mock_df = Mock()
        mock_df.empty = True

        result = AntiCrawlDetector.detect(mock_df, source="akshare")
        # 空数据可能是反爬虫，也可能是真的没数据
        assert result.status in [AntiCrawlStatus.EMPTY_DATA, AntiCrawlStatus.RATE_LIMITED]

    def test_detect_exception_rate_limited(self):
        """测试频率限制异常检测"""
        exc = Exception("429 Too Many Requests")
        result = AntiCrawlDetector.detect(exc, source="akshare")
        assert result.status == AntiCrawlStatus.RATE_LIMITED
        assert result.retry_after is not None

    def test_detect_exception_forbidden(self):
        """测试访问被拒绝异常检测"""
        exc = Exception("403 Forbidden")
        result = AntiCrawlDetector.detect(exc, source="akshare")
        assert result.status == AntiCrawlStatus.BLOCKED
        assert result.retry_after is not None

    def test_detect_exception_json_error(self):
        """测试JSON解析错误检测（可能是反爬虫返回HTML）"""
        exc = ValueError("Expecting value: line 1 column 1 (char 0)")
        result = AntiCrawlDetector.detect(exc, source="akshare")
        assert result.status == AntiCrawlStatus.BLOCKED

    def test_detect_exception_cmsarticlewebold(self):
        """测试cmsArticleWebOld字段缺失（东方财富反爬虫特征）"""
        exc = KeyError("cmsArticleWebOld")
        result = AntiCrawlDetector.detect(exc, source="akshare")
        assert result.status == AntiCrawlStatus.BLOCKED

    def test_detect_exception_ssl_error(self):
        """测试SSL错误检测"""
        exc = Exception("SSL: UNEXPECTED_EOF_WHILE_READING")
        result = AntiCrawlDetector.detect(exc, source="akshare")
        assert result.status == AntiCrawlStatus.RATE_LIMITED

    def test_detect_unknown_exception(self):
        """测试未知异常检测"""
        exc = Exception("Some random error")
        result = AntiCrawlDetector.detect(exc, source="akshare")
        assert result.status == AntiCrawlStatus.UNKNOWN_ERROR

    def test_detect_content_with_block_pattern(self):
        """测试响应内容中的反爬虫特征"""
        mock_df = Mock()
        mock_df.empty = False
        mock_df.__len__ = Mock(return_value=100)
        mock_df.to_string = Mock(return_value="访问被拒绝，请稍后再试")

        result = AntiCrawlDetector.detect(mock_df, source="eastmoney")
        assert result.status == AntiCrawlStatus.BLOCKED

    def test_detect_content_with_sina_block_pattern(self):
        """测试新浪财经反爬虫特征"""
        mock_df = Mock()
        mock_df.empty = False
        mock_df.__len__ = Mock(return_value=100)
        mock_df.to_string = Mock(return_value="访问频率过高，请稍后访问")

        result = AntiCrawlDetector.detect(mock_df, source="sina")
        assert result.status == AntiCrawlStatus.BLOCKED

    def test_request_frequency_tracking(self):
        """测试请求频率跟踪"""
        # 记录多次请求
        for _ in range(35):
            AntiCrawlDetector.record_request("test_source")

        # 检查是否被标记为过于频繁
        assert AntiCrawlDetector._is_request_too_frequent("test_source") is True

    def test_request_frequency_within_limit(self):
        """测试请求频率在限制内"""
        # 记录少量请求
        for _ in range(5):
            AntiCrawlDetector.record_request("test_source")

        # 检查是否未被标记为过于频繁
        assert AntiCrawlDetector._is_request_too_frequent("test_source") is False

    def test_get_wait_time(self):
        """测试获取建议等待时间"""
        # 记录多次请求
        for _ in range(5):
            AntiCrawlDetector.record_request("test_source")

        # 检查建议等待时间
        wait_time = AntiCrawlDetector.get_wait_time("test_source")
        assert wait_time >= 0.0

    def test_small_dataframe_with_symbol(self):
        """测试少量数据（有股票代码）"""
        mock_df = Mock()
        mock_df.empty = False
        mock_df.__len__ = Mock(return_value=5)

        result = AntiCrawlDetector.detect(mock_df, source="akshare", symbol="000001")
        # 有股票代码时，少量数据可能是正常的
        assert result.status == AntiCrawlStatus.NORMAL

    def test_small_dataframe_without_symbol(self):
        """测试少量数据（无股票代码）"""
        mock_df = Mock()
        mock_df.empty = False
        mock_df.__len__ = Mock(return_value=5)
        mock_df.to_string = Mock(return_value="正常数据")

        result = AntiCrawlDetector.detect(mock_df, source="akshare")
        # 无股票代码时，少量数据可能被标记为可疑
        assert result.status in [AntiCrawlStatus.NORMAL, AntiCrawlStatus.RATE_LIMITED]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
