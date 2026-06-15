"""
港股新闻数据提供器
支持从东方财富(AKShare)获取港股新闻数据
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class HKNewsProvider:
    """港股新闻数据提供器"""

    def __init__(self):
        self._connected = False

    async def connect(self):
        self._connected = True

    async def disconnect(self):
        self._connected = False

    def is_available(self) -> bool:
        try:
            import akshare

            return True
        except ImportError:
            return False

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """标准化港股代码为6位数字格式（东方财富要求）"""
        clean = symbol.replace(".HK", "").replace(".hk", "").strip()
        return clean.zfill(6)

    def get_stock_news_sync(self, symbol: str, limit: int = 10) -> pd.DataFrame | None:
        """
        同步获取港股个股新闻（返回原始 DataFrame）

        Args:
            symbol: 港股代码（如 '00700'、'0700.HK'）
            limit: 返回数量限制

        Returns:
            新闻 DataFrame 或 None
        """
        if not self.is_available():
            return None

        try:
            import json
            import time

            import akshare as ak

            symbol_6 = self._normalize_symbol(symbol)
            logger.info(f"📰 [港股新闻] 获取东方财富新闻: {symbol} -> {symbol_6}")

            max_retries = 3
            retry_delay = 1
            news_df = None

            for attempt in range(max_retries):
                try:
                    news_df = ak.stock_news_em(symbol=symbol_6)
                    break
                except json.JSONDecodeError as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"⚠️ [港股新闻] {symbol} 第{attempt + 1}次获取失败(JSON解析错误)，{retry_delay}秒后重试..."
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        logger.error(f"❌ [港股新闻] {symbol} 获取失败(JSON解析错误): {e}")
                        return None
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"⚠️ [港股新闻] {symbol} 第{attempt + 1}次获取失败: {e}，{retry_delay}秒后重试..."
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise

            if news_df is not None and not news_df.empty:
                logger.info(f"✅ [港股新闻] {symbol} 获取成功: {len(news_df)} 条")
                return news_df.head(limit) if limit else news_df
            else:
                logger.warning(f"⚠️ [港股新闻] {symbol} 未获取到数据")
                return None

        except Exception as e:
            logger.error(f"❌ [港股新闻] 获取失败: {e}")
            return None

    async def get_stock_news(self, symbol: str, limit: int = 10) -> list[dict[str, Any]] | None:
        """
        异步获取港股个股新闻（返回结构化列表）

        Args:
            symbol: 港股代码
            limit: 返回数量限制

        Returns:
            新闻列表
        """
        if not self.is_available():
            return None

        try:
            import json

            import akshare as ak

            symbol_6 = self._normalize_symbol(symbol)
            logger.info(f"📰 [港股新闻] 异步获取东方财富新闻: {symbol} -> {symbol_6}")

            max_retries = 3
            retry_delay = 1
            news_df = None

            for attempt in range(max_retries):
                try:
                    news_df = await asyncio.to_thread(ak.stock_news_em, symbol=symbol_6)
                    break
                except json.JSONDecodeError as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"⚠️ [港股新闻] {symbol} 第{attempt + 1}次获取失败(JSON解析错误)，{retry_delay}秒后重试..."
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        logger.error(f"❌ [港股新闻] {symbol} 获取失败(JSON解析错误): {e}")
                        return []
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"⚠️ [港股新闻] {symbol} 第{attempt + 1}次获取失败: {e}，{retry_delay}秒后重试..."
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise

            if news_df is not None and not news_df.empty:
                news_list = []
                for _, row in news_df.head(limit).iterrows():
                    title = str(row.get("新闻标题", "") or row.get("标题", ""))
                    content = str(row.get("新闻内容", "") or row.get("内容", ""))
                    summary = str(row.get("新闻摘要", "") or row.get("摘要", ""))

                    news_item = {
                        "symbol": symbol_6,
                        "title": title,
                        "content": content,
                        "summary": summary,
                        "url": str(row.get("新闻链接", "") or row.get("链接", "")),
                        "source": str(row.get("文章来源", "") or row.get("来源", "") or "东方财富"),
                        "author": str(row.get("作者", "") or ""),
                        "publish_time": self._parse_news_time(row.get("发布时间", "") or row.get("时间", "")),
                        "category": self._classify_news(content, title),
                        "sentiment": self._analyze_news_sentiment(content, title),
                        "sentiment_score": self._calculate_sentiment_score(content, title),
                        "keywords": self._extract_keywords(content, title),
                        "importance": self._assess_news_importance(content, title),
                        "data_source": "akshare",
                    }

                    if news_item["title"]:
                        news_list.append(news_item)

                logger.info(f"✅ [港股新闻] {symbol} 异步获取成功: {len(news_list)} 条")
                return news_list
            else:
                logger.warning(f"⚠️ [港股新闻] {symbol} 未获取到数据")
                return []

        except Exception as e:
            logger.error(f"❌ [港股新闻] 异步获取失败: {e}")
            return []

    # -- 新闻分析辅助方法 --

    @staticmethod
    def _parse_news_time(time_str: str) -> datetime | None:
        """解析新闻时间"""
        if not time_str:
            return datetime.utcnow()

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y/%m/%d",
            "%m-%d %H:%M",
            "%m/%d %H:%M",
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(str(time_str), fmt)
                if fmt in ("%m-%d %H:%M", "%m/%d %H:%M"):
                    parsed = parsed.replace(year=datetime.now().year)
                return parsed
            except ValueError:
                continue

        logger.debug(f"⚠️ 无法解析新闻时间: {time_str}")
        return datetime.utcnow()

    @staticmethod
    def _analyze_news_sentiment(content: str, title: str) -> str:
        """分析新闻情绪"""
        text = f"{title} {content}".lower()

        positive_keywords = [
            "利好",
            "上涨",
            "增长",
            "盈利",
            "突破",
            "创新高",
            "买入",
            "推荐",
            "看好",
            "乐观",
            "强势",
            "大涨",
            "飙升",
            "暴涨",
            "涨停",
            "涨幅",
            "业绩增长",
            "营收增长",
            "净利润增长",
            "扭亏为盈",
            "超预期",
            "获批",
            "中标",
            "签约",
            "合作",
            "并购",
            "重组",
            "分红",
            "回购",
        ]
        negative_keywords = [
            "利空",
            "下跌",
            "亏损",
            "风险",
            "暴跌",
            "卖出",
            "警告",
            "下调",
            "看空",
            "悲观",
            "弱势",
            "大跌",
            "跳水",
            "跌停",
            "跌幅",
            "业绩下滑",
            "营收下降",
            "净利润下降",
            "低于预期",
            "被查",
            "违规",
            "处罚",
            "诉讼",
            "退市",
            "停牌",
            "商誉减值",
        ]

        positive_count = sum(1 for kw in positive_keywords if kw in text)
        negative_count = sum(1 for kw in negative_keywords if kw in text)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"

    @staticmethod
    def _calculate_sentiment_score(content: str, title: str) -> float:
        """计算情绪分数 (-1.0 ~ 1.0)"""
        text = f"{title} {content}".lower()

        positive_weights = {
            "涨停": 1.0,
            "暴涨": 0.9,
            "大涨": 0.8,
            "飙升": 0.8,
            "创新高": 0.7,
            "突破": 0.6,
            "上涨": 0.5,
            "增长": 0.4,
            "利好": 0.6,
            "看好": 0.5,
            "推荐": 0.5,
            "买入": 0.6,
        }
        negative_weights = {
            "跌停": -1.0,
            "暴跌": -0.9,
            "大跌": -0.8,
            "跳水": -0.8,
            "创新低": -0.7,
            "破位": -0.6,
            "下跌": -0.5,
            "下滑": -0.4,
            "利空": -0.6,
            "看空": -0.5,
            "卖出": -0.6,
            "警告": -0.5,
        }

        score = 0.0
        for kw, w in positive_weights.items():
            if kw in text:
                score += w
        for kw, w in negative_weights.items():
            if kw in text:
                score += w

        return max(-1.0, min(1.0, score / 3.0))

    @staticmethod
    def _extract_keywords(content: str, title: str) -> list[str]:
        """提取关键词"""
        text = f"{title} {content}"
        common_keywords = [
            "股票",
            "公司",
            "市场",
            "投资",
            "业绩",
            "财报",
            "政策",
            "行业",
            "分析",
            "预测",
            "涨停",
            "跌停",
            "上涨",
            "下跌",
            "盈利",
            "亏损",
            "并购",
            "重组",
            "分红",
            "回购",
            "增持",
            "减持",
            "融资",
            "IPO",
            "监管",
            "央行",
            "利率",
            "汇率",
            "GDP",
            "通胀",
            "经济",
            "贸易",
            "港股",
            "恒生",
            "纳斯达克",
            "联交所",
            "H股",
            "红筹",
            "内地",
            "增长",
            "下降",
            "营收",
            "利润",
            "净利润",
        ]
        return [kw for kw in common_keywords if kw in text][:10]

    @staticmethod
    def _assess_news_importance(content: str, title: str) -> str:
        """评估新闻重要性"""
        text = f"{title} {content}".lower()

        high_keywords = [
            "业绩",
            "财报",
            "年报",
            "季报",
            "重大",
            "公告",
            "监管",
            "政策",
            "并购",
            "重组",
            "退市",
            "停牌",
            "涨停",
            "跌停",
            "暴涨",
            "暴跌",
            "央行",
            "证监会",
            "交易所",
            "违规",
            "处罚",
            "立案",
            "调查",
        ]
        medium_keywords = [
            "分析",
            "预测",
            "观点",
            "建议",
            "行业",
            "市场",
            "趋势",
            "机会",
            "研报",
            "评级",
            "目标价",
            "增持",
            "减持",
            "买入",
            "卖出",
            "合作",
            "签约",
            "中标",
            "获批",
            "分红",
            "回购",
        ]

        if any(kw in text for kw in high_keywords):
            return "high"
        if any(kw in text for kw in medium_keywords):
            return "medium"
        return "low"

    @staticmethod
    def _classify_news(content: str, title: str) -> str:
        """分类新闻"""
        text = f"{title} {content}".lower()

        if any(kw in text for kw in ["公告", "业绩", "财报", "年报", "季报"]):
            return "company_announcement"
        if any(kw in text for kw in ["政策", "监管", "央行", "证监会", "国务院"]):
            return "policy_news"
        if any(kw in text for kw in ["行业", "板块", "产业", "领域"]):
            return "industry_news"
        if any(kw in text for kw in ["市场", "指数", "大盘", "恒生"]):
            return "market_news"
        if any(kw in text for kw in ["研报", "分析", "评级", "目标价", "机构"]):
            return "research_report"
        return "global"


# 全局实例
_hk_news_provider = None


def get_hk_news_provider() -> HKNewsProvider:
    """获取港股新闻提供器实例"""
    global _hk_news_provider
    if _hk_news_provider is None:
        _hk_news_provider = HKNewsProvider()
    return _hk_news_provider


def get_hk_stock_news_sync(symbol: str, limit: int = 10) -> pd.DataFrame | None:
    """便捷函数：同步获取港股新闻"""
    provider = get_hk_news_provider()
    return provider.get_stock_news_sync(symbol, limit)
