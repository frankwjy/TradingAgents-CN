"""
Enhanced news retriever - combines news retrieval with relevance filtering.

Provides a unified interface for fetching news and applying relevance filters
to reduce noise from unrelated articles (ETF mentions, index fund news, etc.).
"""

import logging
from typing import List, Dict, Optional
import pandas as pd

from .news_filter import create_news_filter, get_company_name, NewsRelevanceFilter
from .enhanced_news_filter import create_enhanced_news_filter

logger = logging.getLogger(__name__)


class EnhancedNewsRetriever:
    """
    Retrieves and filters news for a specific stock.

    Combines AKShare data retrieval with relevance-based filtering to ensure
    only news directly related to the target stock is returned.
    """

    def __init__(self, stock_code: str, use_semantic: bool = False,
                 use_local_model: bool = False, min_score: float = 30):
        """
        Args:
            stock_code: Stock code (e.g. "600036")
            use_semantic: Use semantic similarity for filtering (requires sentence-transformers)
            use_local_model: Use local classification model (requires transformers)
            min_score: Minimum relevance score threshold (0-100)
        """
        self.stock_code = stock_code
        self.clean_code = stock_code.split('.')[0]
        self.use_semantic = use_semantic
        self.use_local_model = use_local_model
        self.min_score = min_score
        self.company_name = get_company_name(self.clean_code)

        self._filter = create_enhanced_news_filter(
            self.clean_code,
            use_semantic=use_semantic,
            use_local_model=use_local_model,
        )

    def retrieve_filtered_news(self, max_news: int = 20) -> Optional[pd.DataFrame]:
        """
        Retrieve news from AKShare and apply relevance filtering.

        Args:
            max_news: Maximum number of news items to retrieve

        Returns:
            Filtered DataFrame with relevance scores, or None if no news found
        """
        try:
            from tradingagents.dataflows.providers.china.akshare import AKShareProvider

            provider = AKShareProvider()
            news_df = provider.get_stock_news_sync(symbol=self.clean_code, limit=max_news)

            if news_df is None or news_df.empty:
                logger.info(f"[增强新闻检索] {self.clean_code} 未获取到新闻")
                return None

            logger.info(f"[增强新闻检索] 获取到 {len(news_df)} 条新闻，开始过滤")

            filtered_df = self._filter.filter_news_enhanced(
                news_df, min_score=self.min_score
            )

            if filtered_df.empty:
                logger.info(f"[增强新闻检索] 过滤后无相关新闻，返回全部原始新闻")
                return news_df

            logger.info(
                f"[增强新闻检索] 过滤完成: {len(news_df)}条 → {len(filtered_df)}条"
            )
            return filtered_df

        except Exception as e:
            logger.error(f"[增强新闻检索] 新闻检索失败: {e}")
            return None

    def filter_dataframe(self, news_df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply relevance filtering to an existing news DataFrame.

        Args:
            news_df: DataFrame with '新闻标题'/'标题' and '新闻内容'/'内容' columns

        Returns:
            Filtered DataFrame with relevance scores
        """
        if news_df is None or news_df.empty:
            return news_df
        return self._filter.filter_news_enhanced(news_df, min_score=self.min_score)

    def get_statistics(self, original_df: pd.DataFrame,
                       filtered_df: pd.DataFrame) -> Dict:
        """Get filtering statistics."""
        score_col = 'final_score' if 'final_score' in filtered_df.columns else 'relevance_score'
        stats = {
            'original_count': len(original_df),
            'filtered_count': len(filtered_df),
            'filter_rate': (len(original_df) - len(filtered_df)) / len(original_df) * 100 if len(original_df) > 0 else 0,
            'avg_score': filtered_df[score_col].mean() if not filtered_df.empty else 0,
            'max_score': filtered_df[score_col].max() if not filtered_df.empty else 0,
            'min_score': filtered_df[score_col].min() if not filtered_df.empty else 0,
        }
        return stats


def create_enhanced_news_retriever(
    stock_code: str,
    use_semantic: bool = False,
    use_local_model: bool = False,
    min_score: float = 30,
) -> EnhancedNewsRetriever:
    """
    Convenience factory for creating an EnhancedNewsRetriever.

    Args:
        stock_code: Stock code (e.g. "600036")
        use_semantic: Use semantic similarity filtering
        use_local_model: Use local classification model
        min_score: Minimum relevance score threshold

    Returns:
        Configured EnhancedNewsRetriever instance
    """
    return EnhancedNewsRetriever(
        stock_code=stock_code,
        use_semantic=use_semantic,
        use_local_model=use_local_model,
        min_score=min_score,
    )
