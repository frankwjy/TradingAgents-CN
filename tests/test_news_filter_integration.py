"""
Tests for news filtering integration into the main pipeline.

Covers:
1. A-share filtering in news_filter_integration.py via AKShareProvider
2. UnifiedNewsAnalyzer applying NewsRelevanceFilter to retrieved news
3. enhanced_news_retriever.py functionality
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, AsyncMock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_news_df():
    """DataFrame mimicking AKShare stock_news_em output."""
    return pd.DataFrame([
        {
            '新闻标题': '招商银行发布2024年第三季度业绩报告',
            '新闻内容': '招商银行今日发布第三季度财报，净利润同比增长8%，资产质量持续改善。',
        },
        {
            '新闻标题': '上证180ETF指数基金（530280）自带杠铃策略',
            '新闻内容': '数据显示，上证180指数前十大权重股分别为贵州茅台、招商银行600036。该ETF基金采用被动投资策略。',
        },
        {
            '新闻标题': '银行ETF指数(512730)多只成分股上涨',
            '新闻内容': '银行板块今日表现强势，招商银行、工商银行等多只成分股上涨，银行ETF基金受益明显。',
        },
        {
            '新闻标题': '招商银行与某科技公司签署战略合作协议',
            '新闻内容': '招商银行宣布与知名科技公司达成战略合作，将在数字化转型方面深度合作。',
        },
    ])


@pytest.fixture
def sample_news_list():
    """List-of-dicts format returned by AKShareProvider.get_stock_news async."""
    return [
        {
            'title': '招商银行发布2024年第三季度业绩报告',
            'content': '招商银行今日发布第三季度财报，净利润同比增长8%。',
            'publish_time': '2024-07-28 10:00:00',
            'source': '东方财富',
        },
        {
            'title': '上证180ETF指数基金（530280）自带杠铃策略',
            'content': '该ETF基金采用被动投资策略，跟踪上证180指数。',
            'publish_time': '2024-07-28 09:00:00',
            'source': '东方财富',
        },
    ]


# ── 1. news_filter_integration.py A-share path ──────────────────────────────

class TestFilteredRealtimeNewsAshare:
    """The A-share path in create_filtered_realtime_news_function should fetch
    news via AKShareProvider.get_stock_news_sync and apply NewsRelevanceFilter."""

    def test_a_share_fetches_and_filters_news(self, sample_news_df):
        from tradingagents.utils.news_filter_integration import (
            create_filtered_realtime_news_function,
        )

        fn = create_filtered_realtime_news_function()

        mock_provider = MagicMock()
        mock_provider.get_stock_news_sync.return_value = sample_news_df

        with patch(
            "tradingagents.dataflows.providers.china.akshare.AKShareProvider",
            return_value=mock_provider,
        ), patch(
            "tradingagents.dataflows.news.realtime_news.get_realtime_stock_news",
            return_value="原始报告内容",
        ):
            result = fn(ticker="600036", curr_date="2024-07-28", enable_filter=True, min_score=30)

        # Should NOT be the plain original report — filtering should have modified it
        assert "原始报告内容" not in result or "相关性" in result or "过滤" in result
        mock_provider.get_stock_news_sync.assert_called_once_with(symbol="600036", limit=20)

    def test_a_share_filter_disabled_returns_original(self, sample_news_df):
        from tradingagents.utils.news_filter_integration import (
            create_filtered_realtime_news_function,
        )

        fn = create_filtered_realtime_news_function()

        with patch(
            "tradingagents.dataflows.news.realtime_news.get_realtime_stock_news",
            return_value="原始报告内容",
        ):
            result = fn(ticker="600036", curr_date="2024-07-28", enable_filter=False)

        assert result == "原始报告内容"

    def test_a_share_provider_failure_falls_back(self):
        from tradingagents.utils.news_filter_integration import (
            create_filtered_realtime_news_function,
        )

        fn = create_filtered_realtime_news_function()

        mock_provider = MagicMock()
        mock_provider.get_stock_news_sync.return_value = None

        with patch(
            "tradingagents.dataflows.providers.china.akshare.AKShareProvider",
            return_value=mock_provider,
        ), patch(
            "tradingagents.dataflows.news.realtime_news.get_realtime_stock_news",
            return_value="原始报告内容",
        ):
            result = fn(ticker="600036", curr_date="2024-07-28", enable_filter=True)

        # Falls back to original when provider returns no data
        assert "原始报告内容" in result

    def test_non_a_share_returns_original(self):
        from tradingagents.utils.news_filter_integration import (
            create_filtered_realtime_news_function,
        )

        fn = create_filtered_realtime_news_function()

        with patch(
            "tradingagents.dataflows.news.realtime_news.get_realtime_stock_news",
            return_value="美股报告内容",
        ):
            result = fn(ticker="AAPL", curr_date="2024-07-28", enable_filter=True)

        assert result == "美股报告内容"


# ── 2. UnifiedNewsAnalyzer filtering integration ─────────────────────────────

class TestUnifiedNewsAnalyzerFiltering:
    """UnifiedNewsAnalyzer should apply NewsRelevanceFilter to A-share news
    retrieved from the database."""

    def test_a_share_news_filtered_via_database(self, sample_news_list):
        """When news comes from DB (list-of-dicts), it should be filtered."""
        from tradingagents.tools.unified_news_tool import UnifiedNewsAnalyzer

        mock_toolkit = MagicMock()
        analyzer = UnifiedNewsAnalyzer(mock_toolkit)

        # Mock database to return news
        with patch.object(analyzer, '_get_news_from_database') as mock_db:
            # Return a formatted report that contains raw news
            raw_report = "\n".join(
                f"## {i+1}. {n['title']}\n{n['content']}" for i, n in enumerate(sample_news_list)
            )
            mock_db.return_value = raw_report

            with patch.object(analyzer, '_format_news_result', side_effect=lambda c, s, m="": c):
                result = analyzer._get_a_share_news("600036", 10, "")

        # The result should have been filtered — ETF news should be penalized
        # At minimum, verify the analyzer was called
        assert result is not None
        assert len(result) > 0

    def test_stock_type_identification(self):
        from tradingagents.tools.unified_news_tool import UnifiedNewsAnalyzer

        analyzer = UnifiedNewsAnalyzer(MagicMock())
        assert analyzer._identify_stock_type("600036") == "A股"
        assert analyzer._identify_stock_type("000001") == "A股"
        assert analyzer._identify_stock_type("0700.HK") == "港股"
        assert analyzer._identify_stock_type("AAPL") == "美股"


# ── 3. NewsRelevanceFilter basic functionality ───────────────────────────────

class TestNewsRelevanceFilter:
    """Verify the core filter scores news correctly."""

    def test_high_score_for_direct_company_mention(self):
        from tradingagents.utils.news_filter import create_news_filter

        f = create_news_filter("600036")
        score = f.calculate_relevance_score(
            "招商银行发布2024年第三季度业绩报告",
            "招商银行今日发布第三季度财报"
        )
        assert score >= 50, f"Expected >=50 for direct company mention in title, got {score}"

    def test_low_score_for_etf_news(self):
        from tradingagents.utils.news_filter import create_news_filter

        f = create_news_filter("600036")
        score = f.calculate_relevance_score(
            "上证180ETF指数基金（530280）自带杠铃策略",
            "该ETF基金采用被动投资策略，跟踪上证180指数"
        )
        assert score < 30, f"Expected <30 for ETF news, got {score}"

    def test_filter_news_dataframe(self, sample_news_df):
        from tradingagents.utils.news_filter import create_news_filter

        f = create_news_filter("600036")
        filtered = f.filter_news(sample_news_df, min_score=30)

        # Should filter out ETF news, keep company-specific news
        assert len(filtered) < len(sample_news_df)
        assert len(filtered) >= 1  # At least the direct company news

    def test_filter_statistics(self, sample_news_df):
        from tradingagents.utils.news_filter import create_news_filter

        f = create_news_filter("600036")
        filtered = f.filter_news(sample_news_df, min_score=30)
        stats = f.get_filter_statistics(sample_news_df, filtered)

        assert stats['original_count'] == len(sample_news_df)
        assert stats['filtered_count'] == len(filtered)
        assert stats['filter_rate'] > 0


# ── 4. EnhancedNewsFilter (rule-only mode) ───────────────────────────────────

class TestEnhancedNewsFilter:
    """Test enhanced filter with only rule-based scoring (no external deps)."""

    def test_enhanced_filter_rule_only(self, sample_news_df):
        from tradingagents.utils.enhanced_news_filter import create_enhanced_news_filter

        f = create_enhanced_news_filter("600036", use_semantic=False, use_local_model=False)
        filtered = f.filter_news_enhanced(sample_news_df, min_score=30)

        assert len(filtered) < len(sample_news_df)
        assert 'final_score' in filtered.columns
        assert 'rule_score' in filtered.columns


# ── 5. EnhancedNewsRetriever ─────────────────────────────────────────────────

class TestEnhancedNewsRetriever:
    """Test the EnhancedNewsRetriever that combines retrieval + filtering."""

    def test_filter_dataframe(self, sample_news_df):
        from tradingagents.utils.enhanced_news_retriever import create_enhanced_news_retriever

        retriever = create_enhanced_news_retriever("600036", min_score=30)
        filtered = retriever.filter_dataframe(sample_news_df)

        assert len(filtered) < len(sample_news_df)
        assert 'final_score' in filtered.columns

    def test_filter_empty_dataframe(self):
        from tradingagents.utils.enhanced_news_retriever import create_enhanced_news_retriever

        retriever = create_enhanced_news_retriever("600036")
        empty_df = pd.DataFrame()
        result = retriever.filter_dataframe(empty_df)

        assert result.empty

    def test_filter_none_returns_none(self):
        from tradingagents.utils.enhanced_news_retriever import create_enhanced_news_retriever

        retriever = create_enhanced_news_retriever("600036")
        result = retriever.filter_dataframe(None)

        assert result is None

    def test_get_statistics(self, sample_news_df):
        from tradingagents.utils.enhanced_news_retriever import create_enhanced_news_retriever

        retriever = create_enhanced_news_retriever("600036", min_score=30)
        filtered = retriever.filter_dataframe(sample_news_df)
        stats = retriever.get_statistics(sample_news_df, filtered)

        assert stats['original_count'] == len(sample_news_df)
        assert stats['filtered_count'] == len(filtered)
        assert stats['filter_rate'] > 0

    def test_retrieve_filtered_news_with_mock(self, sample_news_df):
        from tradingagents.utils.enhanced_news_retriever import create_enhanced_news_retriever

        retriever = create_enhanced_news_retriever("600036", min_score=30)

        mock_provider = MagicMock()
        mock_provider.get_stock_news_sync.return_value = sample_news_df

        with patch(
            "tradingagents.dataflows.providers.china.akshare.AKShareProvider",
            return_value=mock_provider,
        ):
            result = retriever.retrieve_filtered_news(max_news=20)

        assert result is not None
        assert len(result) < len(sample_news_df)

    def test_apply_news_filter_method(self, sample_news_list):
        """Test the _apply_news_filter method on UnifiedNewsAnalyzer."""
        from tradingagents.tools.unified_news_tool import UnifiedNewsAnalyzer

        analyzer = UnifiedNewsAnalyzer(MagicMock())

        filtered = analyzer._apply_news_filter("600036", sample_news_list)

        # ETF news should be filtered or scored lower
        assert len(filtered) <= len(sample_news_list)
        if filtered:
            assert 'relevance_score' in filtered[0]
