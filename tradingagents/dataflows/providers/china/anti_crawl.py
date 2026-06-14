"""
反爬虫检测模块
检测AKShare请求是否被反爬虫机制拦截，区分"无数据"和"被封锁"
"""
import logging
import time
from typing import Optional, Any, Dict
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AntiCrawlStatus(Enum):
    """反爬虫状态枚举"""
    NORMAL = "normal"  # 正常
    RATE_LIMITED = "rate_limited"  # 被限速
    BLOCKED = "blocked"  # 被封锁
    EMPTY_DATA = "empty_data"  # 空数据（可能是反爬虫，也可能是真的没数据）
    UNKNOWN_ERROR = "unknown_error"  # 未知错误


@dataclass
class AntiCrawlResult:
    """反爬虫检测结果"""
    status: AntiCrawlStatus
    message: str
    retry_after: Optional[float] = None  # 建议等待时间（秒）
    raw_response: Any = None  # 原始响应数据


class AntiCrawlDetector:
    """
    反爬虫检测器
    检测AKShare请求是否被反爬虫机制拦截
    """

    # 东方财富网常见的反爬虫响应特征
    EASTMONEY_BLOCK_PATTERNS = [
        "访问被拒绝",
        "Access Denied",
        "请求过于频繁",
        "请稍后再试",
        "IP被封禁",
        "验证码",
        "captcha",
        "blocked",
        "forbidden",
    ]

    # 新浪财经常见的反爬虫响应特征
    SINA_BLOCK_PATTERNS = [
        "访问频率过高",
        "请稍后访问",
        "IP限制",
        "流量限制",
    ]

    # 空数据阈值（如果返回的数据量低于此值，可能是反爬虫）
    EMPTY_DATA_THRESHOLD = 10

    # 最近请求记录（用于检测频率限制）
    _request_history: Dict[str, list] = {}
    _history_window: float = 60.0  # 60秒窗口

    @classmethod
    def detect(
        cls,
        response: Any,
        source: str = "akshare",
        url: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> AntiCrawlResult:
        """
        检测响应是否被反爬虫拦截

        Args:
            response: AKShare返回的响应（DataFrame、dict、或异常）
            source: 数据源标识（akshare/eastmoney/sina）
            url: 请求URL（可选）
            symbol: 股票代码（可选）

        Returns:
            AntiCrawlResult: 检测结果
        """
        # 1. 检查是否是异常
        if isinstance(response, Exception):
            return cls._detect_from_exception(response, source)

        # 2. 检查是否是None或空
        if response is None:
            return AntiCrawlResult(
                status=AntiCrawlStatus.EMPTY_DATA,
                message="响应为None",
            )

        # 3. 检查DataFrame是否为空
        if hasattr(response, 'empty') and response.empty:
            return cls._detect_empty_response(source, url, symbol)

        # 4. 检查DataFrame行数（如果行数过少，可能是反爬虫）
        if hasattr(response, '__len__') and len(response) < cls.EMPTY_DATA_THRESHOLD:
            # 对于某些接口，少量数据是正常的
            if symbol and len(response) > 0:
                return AntiCrawlResult(
                    status=AntiCrawlStatus.NORMAL,
                    message=f"返回{len(response)}条数据",
                )
            return cls._detect_suspicious_data(response, source)

        # 5. 检查响应内容中是否有反爬虫特征
        if hasattr(response, 'to_string'):
            content = response.to_string()
            block_result = cls._detect_from_content(content, source)
            if block_result.status != AntiCrawlStatus.NORMAL:
                return block_result

        return AntiCrawlResult(
            status=AntiCrawlStatus.NORMAL,
            message="响应正常",
        )

    @classmethod
    def _detect_from_exception(cls, exc: Exception, source: str) -> AntiCrawlResult:
        """从异常中检测反爬虫"""
        error_str = str(exc).lower()

        # 检查是否是频率限制错误
        if any(keyword in error_str for keyword in ["429", "too many requests", "rate limit"]):
            return AntiCrawlResult(
                status=AntiCrawlStatus.RATE_LIMITED,
                message=f"检测到频率限制: {exc}",
                retry_after=5.0,
            )

        # 检查是否是访问被拒绝
        if any(keyword in error_str for keyword in ["403", "forbidden", "access denied", "blocked"]):
            return AntiCrawlResult(
                status=AntiCrawlStatus.BLOCKED,
                message=f"检测到访问被拒绝: {exc}",
                retry_after=30.0,
            )

        # 检查是否是JSON解析错误（可能是返回了HTML错误页面）
        if isinstance(exc, (ValueError, KeyError)):
            if "json" in error_str or "cmsarticlewebold" in error_str or "expecting value" in error_str:
                return AntiCrawlResult(
                    status=AntiCrawlStatus.BLOCKED,
                    message=f"检测到响应格式异常（可能是反爬虫）: {exc}",
                    retry_after=10.0,
                )

        # SSL错误也可能是反爬虫
        if "ssl" in error_str or "unexpected_eof" in error_str:
            return AntiCrawlResult(
                status=AntiCrawlStatus.RATE_LIMITED,
                message=f"检测到SSL错误（可能是频率限制）: {exc}",
                retry_after=3.0,
            )

        return AntiCrawlResult(
            status=AntiCrawlStatus.UNKNOWN_ERROR,
            message=f"未知错误: {exc}",
        )

    @classmethod
    def _detect_empty_response(
        cls, source: str, url: Optional[str], symbol: Optional[str]
    ) -> AntiCrawlResult:
        """检测空响应是否是反爬虫"""
        # 检查请求频率
        if cls._is_request_too_frequent(source):
            return AntiCrawlResult(
                status=AntiCrawlStatus.RATE_LIMITED,
                message="请求过于频繁，返回空数据",
                retry_after=2.0,
            )

        # 对于某些接口，空数据可能是正常的
        if symbol:
            # 个股数据为空可能是股票代码不存在
            return AntiCrawlResult(
                status=AntiCrawlStatus.EMPTY_DATA,
                message=f"股票{symbol}无数据",
            )

        return AntiCrawlResult(
            status=AntiCrawlStatus.EMPTY_DATA,
            message="返回空数据",
        )

    @classmethod
    def _detect_suspicious_data(cls, response: Any, source: str) -> AntiCrawlResult:
        """检测可疑数据（数据量过少）"""
        # 检查请求频率
        if cls._is_request_too_frequent(source):
            return AntiCrawlResult(
                status=AntiCrawlStatus.RATE_LIMITED,
                message=f"数据量异常（{len(response)}条），可能是频率限制",
                retry_after=2.0,
            )

        return AntiCrawlResult(
            status=AntiCrawlStatus.NORMAL,
            message=f"返回{len(response)}条数据",
        )

    @classmethod
    def _detect_from_content(cls, content: str, source: str) -> AntiCrawlResult:
        """从响应内容中检测反爬虫"""
        content_lower = content.lower()

        # 检查东方财富网特征
        if source in ("eastmoney", "akshare"):
            for pattern in cls.EASTMONEY_BLOCK_PATTERNS:
                if pattern.lower() in content_lower:
                    return AntiCrawlResult(
                        status=AntiCrawlStatus.BLOCKED,
                        message=f"检测到反爬虫特征: {pattern}",
                        retry_after=15.0,
                    )

        # 检查新浪财经特征
        if source in ("sina", "akshare"):
            for pattern in cls.SINA_BLOCK_PATTERNS:
                if pattern.lower() in content_lower:
                    return AntiCrawlResult(
                        status=AntiCrawlStatus.BLOCKED,
                        message=f"检测到反爬虫特征: {pattern}",
                        retry_after=15.0,
                    )

        return AntiCrawlResult(
            status=AntiCrawlStatus.NORMAL,
            message="响应正常",
        )

    @classmethod
    def _is_request_too_frequent(cls, source: str) -> bool:
        """检查请求是否过于频繁"""
        current_time = time.time()

        if source not in cls._request_history:
            cls._request_history[source] = []

        # 清理过期记录
        cls._request_history[source] = [
            t for t in cls._request_history[source]
            if current_time - t < cls._history_window
        ]

        # 检查频率（每分钟不超过30次）
        if len(cls._request_history[source]) > 30:
            return True

        # 记录本次请求
        cls._request_history[source].append(current_time)
        return False

    @classmethod
    def record_request(cls, source: str) -> None:
        """记录一次请求（用于频率检测）"""
        current_time = time.time()
        if source not in cls._request_history:
            cls._request_history[source] = []
        cls._request_history[source].append(current_time)

    @classmethod
    def get_wait_time(cls, source: str) -> float:
        """获取建议等待时间"""
        current_time = time.time()
        if source not in cls._request_history:
            return 0.0

        recent_requests = [
            t for t in cls._request_history[source]
            if current_time - t < 5.0  # 最近5秒
        ]

        if len(recent_requests) >= 3:
            return 1.0  # 最近5秒内超过3次请求，等待1秒
        return 0.0
