"""
港股新闻功能单元测试
覆盖：代码标准化、情绪分析、新闻分类、关键词提取、重要性评估、数据源优先级、过滤器支持
"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd


class TestHKNewsProviderNormalization(unittest.TestCase):
    """测试港股代码标准化"""

    def test_normalize_5digit_code(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        provider = HKNewsProvider()
        # AKShare stock_news_em 要求6位数字代码
        self.assertEqual(provider._normalize_symbol("00700"), "000700")
        self.assertEqual(provider._normalize_symbol("0700"), "000700")
        self.assertEqual(provider._normalize_symbol("700"), "000700")

    def test_normalize_with_hk_suffix(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        provider = HKNewsProvider()
        self.assertEqual(provider._normalize_symbol("0700.HK"), "000700")
        self.assertEqual(provider._normalize_symbol("00700.HK"), "000700")
        self.assertEqual(provider._normalize_symbol("700.hk"), "000700")


class TestHKNewsSentimentAnalysis(unittest.TestCase):
    """测试港股新闻情绪分析"""

    def test_positive_sentiment(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._analyze_news_sentiment("公司业绩增长超预期，净利润大涨", "腾讯控股发布利好公告")
        self.assertEqual(result, "positive")

    def test_negative_sentiment(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._analyze_news_sentiment("公司业绩下滑，净利润亏损", "股价暴跌，风险警告")
        self.assertEqual(result, "negative")

    def test_neutral_sentiment(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._analyze_news_sentiment("公司召开年度股东大会", "股东大会纪要")
        self.assertEqual(result, "neutral")


class TestHKNewsSentimentScore(unittest.TestCase):
    """测试港股新闻情绪分数"""

    def test_positive_score_range(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        score = HKNewsProvider._calculate_sentiment_score("大涨 利好 暴涨 突破 创新高", "利好消息")
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 1.0)

    def test_negative_score_range(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        score = HKNewsProvider._calculate_sentiment_score("暴跌 利空 大跌 跌停", "利空消息")
        self.assertLess(score, 0)
        self.assertGreaterEqual(score, -1.0)

    def test_neutral_score(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        score = HKNewsProvider._calculate_sentiment_score("公司召开会议", "会议纪要")
        self.assertEqual(score, 0.0)


class TestHKNewsClassification(unittest.TestCase):
    """测试港股新闻分类"""

    def test_company_announcement(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._classify_news("公司发布年度业绩公告", "腾讯控股2024年年报公告")
        self.assertEqual(result, "company_announcement")

    def test_policy_news(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._classify_news("央行发布新政策", "监管政策调整")
        self.assertEqual(result, "policy_news")

    def test_industry_news(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._classify_news("互联网行业发展趋势", "行业板块分析")
        self.assertEqual(result, "industry_news")

    def test_market_news(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._classify_news("恒生指数今日表现", "港股市场分析")
        self.assertEqual(result, "market_news")

    def test_research_report(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._classify_news("机构发布研报，给出目标价", "分析报告评级")
        self.assertEqual(result, "research_report")


class TestHKNewsKeywordExtraction(unittest.TestCase):
    """测试港股新闻关键词提取"""

    def test_extract_basic_keywords(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        keywords = HKNewsProvider._extract_keywords("公司发布业绩报告，净利润增长", "腾讯控股业绩公告")
        self.assertIn("公司", keywords)
        self.assertIn("业绩", keywords)
        self.assertIn("增长", keywords)

    def test_keywords_max_count(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        keywords = HKNewsProvider._extract_keywords(
            "股票 市场 投资 业绩 财报 政策 行业 分析 预测 港股 恒生 并购 重组", "标题"
        )
        self.assertLessEqual(len(keywords), 10)


class TestHKNewsImportanceAssessment(unittest.TestCase):
    """测试港股新闻重要性评估"""

    def test_high_importance(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._assess_news_importance("公司发布年度财报，业绩大幅增长", "腾讯控股年报公告")
        self.assertEqual(result, "high")

    def test_medium_importance(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._assess_news_importance("机构发布研报，给出买入评级", "分析报告")
        self.assertEqual(result, "medium")

    def test_low_importance(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._assess_news_importance("普通新闻内容", "日常动态")
        self.assertEqual(result, "low")


class TestHKNewsProviderAvailability(unittest.TestCase):
    """测试港股新闻提供器可用性"""

    def test_provider_is_available(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        provider = HKNewsProvider()
        # akshare 应该已安装
        self.assertTrue(provider.is_available())

    def test_provider_singleton(self):
        from tradingagents.dataflows.providers.hk.hk_news import get_hk_news_provider

        p1 = get_hk_news_provider()
        p2 = get_hk_news_provider()
        self.assertIs(p1, p2)


class TestHKStockCompanyMapping(unittest.TestCase):
    """测试港股公司名称映射"""

    def test_hk_mapping_exists(self):
        from tradingagents.utils.news_filter import HK_STOCK_COMPANY_MAPPING

        self.assertGreater(len(HK_STOCK_COMPANY_MAPPING), 50)

    def test_major_hk_stocks_mapped(self):
        from tradingagents.utils.news_filter import HK_STOCK_COMPANY_MAPPING

        # 检查主要港股是否在映射中
        major_stocks = ["00700", "09988", "09618", "03690", "00941", "00939", "01398"]
        for code in major_stocks:
            self.assertIn(code, HK_STOCK_COMPANY_MAPPING, f"港股 {code} 应在映射中")

    def test_get_company_name_hk(self):
        from tradingagents.utils.news_filter import get_company_name

        self.assertEqual(get_company_name("00700"), "腾讯控股")
        self.assertEqual(get_company_name("0700.HK"), "腾讯控股")
        self.assertEqual(get_company_name("09988"), "阿里巴巴")

    def test_get_company_name_hk_unknown(self):
        from tradingagents.utils.news_filter import get_company_name

        result = get_company_name("99999")
        self.assertTrue(result.startswith("港股"))

    def test_get_company_name_a_share_unaffected(self):
        from tradingagents.utils.news_filter import get_company_name

        self.assertEqual(get_company_name("600036"), "招商银行")
        self.assertEqual(get_company_name("000001"), "平安银行")


class TestHKNewsFilterIntegration(unittest.TestCase):
    """测试港股新闻过滤器集成"""

    def test_create_news_filter_for_hk(self):
        from tradingagents.utils.news_filter import create_news_filter

        f = create_news_filter("00700")
        self.assertEqual(f.company_name, "腾讯控股")
        self.assertEqual(f.stock_code, "00700")

    def test_filter_hk_news_relevance(self):
        from tradingagents.utils.news_filter import create_news_filter

        f = create_news_filter("00700")

        test_news = pd.DataFrame(
            [
                {"新闻标题": "腾讯控股发布2024年业绩报告", "新闻内容": "腾讯控股今日公布年度业绩，净利润同比增长..."},
                {"新闻标题": "恒生指数今日上涨", "新闻内容": "港股市场整体表现良好，多只成分股上涨..."},
                {"新闻标题": "阿里巴巴发布财报", "新闻内容": "阿里巴巴集团公布季度业绩..."},
            ]
        )

        filtered = f.filter_news(test_news, min_score=30)
        # 第一条应保留（包含公司名），第三条可能保留（包含股票代码间接匹配），第二条可能被过滤
        self.assertGreater(len(filtered), 0)
        # 第一条评分应最高
        if not filtered.empty:
            self.assertIn("腾讯控股", filtered.iloc[0]["新闻标题"])


class TestHKNewsDataSourcePriority(unittest.TestCase):
    """测试港股新闻数据源优先级链"""

    def test_unified_news_tool_identifies_hk(self):
        """测试统一新闻工具能正确识别港股代码"""
        from tradingagents.tools.unified_news_tool import UnifiedNewsAnalyzer

        analyzer = UnifiedNewsAnalyzer(MagicMock())

        # 测试港股代码识别
        self.assertEqual(analyzer._identify_stock_type("00700"), "港股")
        self.assertEqual(analyzer._identify_stock_type("0700.HK"), "港股")
        self.assertEqual(analyzer._identify_stock_type("09988"), "港股")

    def test_unified_news_tool_identifies_non_hk(self):
        """测试统一新闻工具不会误判其他市场"""
        from tradingagents.tools.unified_news_tool import UnifiedNewsAnalyzer

        analyzer = UnifiedNewsAnalyzer(MagicMock())

        # A股
        self.assertEqual(analyzer._identify_stock_type("600036"), "A股")
        self.assertEqual(analyzer._identify_stock_type("000001"), "A股")
        # 美股
        self.assertEqual(analyzer._identify_stock_type("AAPL"), "美股")

    @patch("tradingagents.tools.unified_news_tool.UnifiedNewsAnalyzer._get_news_from_database")
    @patch("tradingagents.tools.unified_news_tool.UnifiedNewsAnalyzer._sync_hk_news_from_provider")
    def test_hk_news_tries_database_first(self, mock_sync, mock_db):
        """测试港股新闻优先从数据库获取"""
        from tradingagents.tools.unified_news_tool import UnifiedNewsAnalyzer

        mock_db.return_value = "# 00700 最新新闻\n\n测试新闻内容"
        analyzer = UnifiedNewsAnalyzer(MagicMock())

        result = analyzer._get_hk_share_news("00700", 10)
        mock_db.assert_called_once_with("00700", 10)
        self.assertIn("数据库缓存", result)

    @patch("tradingagents.tools.unified_news_tool.UnifiedNewsAnalyzer._get_news_from_database")
    @patch("tradingagents.tools.unified_news_tool.UnifiedNewsAnalyzer._sync_hk_news_from_provider")
    def test_hk_news_syncs_when_db_empty(self, mock_sync, mock_db):
        """测试数据库为空时尝试同步"""
        from tradingagents.tools.unified_news_tool import UnifiedNewsAnalyzer

        mock_db.return_value = ""
        mock_sync.return_value = False
        analyzer = UnifiedNewsAnalyzer(MagicMock())

        # 即使同步失败也不应抛异常
        result = analyzer._get_hk_share_news("00700", 10)
        mock_sync.assert_called_once_with("00700", 10)


class TestHKNewsProviderSync(unittest.TestCase):
    """测试港股新闻提供器同步方法"""

    @patch("tradingagents.dataflows.providers.hk.hk_news.HKNewsProvider.is_available", return_value=False)
    def test_sync_returns_none_when_unavailable(self, mock_avail):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        provider = HKNewsProvider()
        result = provider.get_stock_news_sync("00700")
        self.assertIsNone(result)

    @patch("tradingagents.dataflows.providers.hk.hk_news.HKNewsProvider.is_available", return_value=False)
    def test_async_returns_empty_when_unavailable(self, mock_avail):
        import asyncio

        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        provider = HKNewsProvider()
        result = asyncio.get_event_loop().run_until_complete(provider.get_stock_news("00700"))
        self.assertIsNone(result)


class TestHKNewsTimeParsing(unittest.TestCase):
    """测试港股新闻时间解析"""

    def test_parse_standard_format(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._parse_news_time("2024-01-15 10:30:00")
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_date_only(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._parse_news_time("2024-01-15")
        self.assertEqual(result.year, 2024)

    def test_parse_empty_returns_utcnow(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._parse_news_time("")
        self.assertIsInstance(result, datetime)

    def test_parse_slash_format(self):
        from tradingagents.dataflows.providers.hk.hk_news import HKNewsProvider

        result = HKNewsProvider._parse_news_time("2024/01/15 10:30")
        self.assertEqual(result.year, 2024)


class TestHKNewsExports(unittest.TestCase):
    """测试港股新闻模块导出"""

    def test_hk_module_exports(self):
        from tradingagents.dataflows.providers.hk import (
            HK_NEWS_AVAILABLE,
            HKNewsProvider,
            get_hk_news_provider,
            get_hk_stock_news_sync,
        )

        self.assertTrue(HK_NEWS_AVAILABLE)
        self.assertIsNotNone(HKNewsProvider)
        self.assertIsNotNone(get_hk_news_provider)
        self.assertIsNotNone(get_hk_stock_news_sync)


if __name__ == "__main__":
    unittest.main()
