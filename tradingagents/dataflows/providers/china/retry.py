"""
统一重试机制模块
提供可复用的重试装饰器，支持指数退避和反爬虫检测
"""

import asyncio
import functools
import logging
import random
import time
from typing import Any, Callable, Optional, Tuple, Type, TypeVar

from .anti_crawl import AntiCrawlDetector, AntiCrawlStatus

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryExhaustedError(Exception):
    """重试次数耗尽异常"""

    def __init__(self, message: str, last_exception: Exception | None = None):
        super().__init__(message)
        self.last_exception = last_exception


def retry_on_failure(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    retryable_statuses: tuple[AntiCrawlStatus, ...] = (
        AntiCrawlStatus.RATE_LIMITED,
        AntiCrawlStatus.BLOCKED,
    ),
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> Callable:
    """
    重试装饰器（同步版本）

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exponential_base: 指数退避基数
        jitter: 是否添加随机抖动
        retryable_exceptions: 可重试的异常类型
        retryable_statuses: 可重试的反爬虫状态
        on_retry: 重试时的回调函数 (attempt, exception, delay) -> None

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # 检查返回值是否被反爬虫拦截
                    detection = AntiCrawlDetector.detect(result)
                    if detection.status in retryable_statuses:
                        if attempt < max_retries:
                            delay = _calculate_delay(
                                attempt, base_delay, max_delay, exponential_base, jitter, detection.retry_after
                            )
                            logger.warning(
                                f"⚠️ {func.__name__} 检测到反爬虫: {detection.message}, "
                                f"{delay:.1f}秒后重试 (尝试 {attempt + 1}/{max_retries})"
                            )
                            if on_retry:
                                on_retry(attempt, Exception(detection.message), delay)
                            time.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ {func.__name__} 重试次数耗尽: {detection.message}")
                            return result

                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    # 检测异常类型
                    detection = AntiCrawlDetector.detect(e)

                    if attempt < max_retries:
                        delay = _calculate_delay(
                            attempt, base_delay, max_delay, exponential_base, jitter, detection.retry_after
                        )
                        logger.warning(
                            f"⚠️ {func.__name__} 失败: {e}, {delay:.1f}秒后重试 (尝试 {attempt + 1}/{max_retries})"
                        )
                        if on_retry:
                            on_retry(attempt, e, delay)
                        time.sleep(delay)
                    else:
                        logger.error(f"❌ {func.__name__} 重试次数耗尽: {e}")
                        raise RetryExhaustedError(
                            f"{func.__name__} 在{max_retries}次重试后仍然失败", last_exception=e
                        ) from e

            return result

        return wrapper

    return decorator


def async_retry_on_failure(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    retryable_statuses: tuple[AntiCrawlStatus, ...] = (
        AntiCrawlStatus.RATE_LIMITED,
        AntiCrawlStatus.BLOCKED,
    ),
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> Callable:
    """
    重试装饰器（异步版本）

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exponential_base: 指数退避基数
        jitter: 是否添加随机抖动
        retryable_exceptions: 可重试的异常类型
        retryable_statuses: 可重试的反爬虫状态
        on_retry: 重试时的回调函数 (attempt, exception, delay) -> None

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)

                    # 检查返回值是否被反爬虫拦截
                    detection = AntiCrawlDetector.detect(result)
                    if detection.status in retryable_statuses:
                        if attempt < max_retries:
                            delay = _calculate_delay(
                                attempt, base_delay, max_delay, exponential_base, jitter, detection.retry_after
                            )
                            logger.warning(
                                f"⚠️ {func.__name__} 检测到反爬虫: {detection.message}, "
                                f"{delay:.1f}秒后重试 (尝试 {attempt + 1}/{max_retries})"
                            )
                            if on_retry:
                                on_retry(attempt, Exception(detection.message), delay)
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(f"❌ {func.__name__} 重试次数耗尽: {detection.message}")
                            return result

                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    # 检测异常类型
                    detection = AntiCrawlDetector.detect(e)

                    if attempt < max_retries:
                        delay = _calculate_delay(
                            attempt, base_delay, max_delay, exponential_base, jitter, detection.retry_after
                        )
                        logger.warning(
                            f"⚠️ {func.__name__} 失败: {e}, {delay:.1f}秒后重试 (尝试 {attempt + 1}/{max_retries})"
                        )
                        if on_retry:
                            on_retry(attempt, e, delay)
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"❌ {func.__name__} 重试次数耗尽: {e}")
                        raise RetryExhaustedError(
                            f"{func.__name__} 在{max_retries}次重试后仍然失败", last_exception=e
                        ) from e

            return result

        return wrapper

    return decorator


def _calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float,
    jitter: bool,
    suggested_delay: float | None = None,
) -> float:
    """
    计算延迟时间

    Args:
        attempt: 当前尝试次数
        base_delay: 基础延迟时间
        max_delay: 最大延迟时间
        exponential_base: 指数退避基数
        jitter: 是否添加随机抖动
        suggested_delay: 建议的延迟时间（来自反爬虫检测）

    Returns:
        延迟时间（秒）
    """
    # 如果有建议的延迟时间，使用它
    if suggested_delay is not None:
        delay = suggested_delay
    else:
        # 指数退避
        delay = base_delay * (exponential_base**attempt)

    # 添加随机抖动
    if jitter:
        delay = delay * (0.5 + random.random())

    # 限制最大延迟
    return min(delay, max_delay)


class RetryConfig:
    """
    重试配置类
    用于统一管理重试参数
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int, suggested_delay: float | None = None) -> float:
        """计算指定尝试次数的延迟时间"""
        return _calculate_delay(
            attempt,
            self.base_delay,
            self.max_delay,
            self.exponential_base,
            self.jitter,
            suggested_delay,
        )


# 预定义的重试配置
RETRY_CONFIGS = {
    # 快速重试（用于实时行情等低延迟场景）
    "fast": RetryConfig(
        max_retries=2,
        base_delay=0.5,
        max_delay=5.0,
        exponential_base=2.0,
        jitter=True,
    ),
    # 标准重试（用于一般数据获取）
    "standard": RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=15.0,
        exponential_base=2.0,
        jitter=True,
    ),
    # 耐心重试（用于新闻等非实时数据）
    "patient": RetryConfig(
        max_retries=5,
        base_delay=2.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True,
    ),
}
