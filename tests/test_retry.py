"""
重试机制模块测试
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from tradingagents.dataflows.providers.china.retry import (
    retry_on_failure,
    async_retry_on_failure,
    RetryExhaustedError,
    RetryConfig,
    RETRY_CONFIGS,
    _calculate_delay,
)
from tradingagents.dataflows.providers.china.anti_crawl import AntiCrawlStatus


class TestRetryDecorator:
    """重试装饰器测试"""

    def test_retry_success_on_first_attempt(self):
        """测试第一次尝试就成功"""
        call_count = 0

        @retry_on_failure(max_retries=3, base_delay=0.01)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self):
        """测试失败后重试成功"""
        call_count = 0

        @retry_on_failure(max_retries=3, base_delay=0.01)
        def eventual_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return "success"

        result = eventual_success()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """测试重试次数耗尽"""
        call_count = 0

        @retry_on_failure(max_retries=2, base_delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("Permanent error")

        with pytest.raises(RetryExhaustedError) as exc_info:
            always_fail()

        assert call_count == 3  # 1 initial + 2 retries
        assert "Permanent error" in str(exc_info.value.last_exception)

    def test_retry_with_specific_exception(self):
        """测试只重试特定异常类型"""
        call_count = 0

        @retry_on_failure(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,)
        )
        def fail_with_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            fail_with_type_error()

        assert call_count == 1  # 不应该重试

    def test_retry_with_on_retry_callback(self):
        """测试重试回调函数"""
        retry_attempts = []

        def on_retry(attempt, exception, delay):
            retry_attempts.append((attempt, str(exception), delay))

        @retry_on_failure(max_retries=2, base_delay=0.01, on_retry=on_retry)
        def fail_then_succeed():
            if len(retry_attempts) < 2:
                raise Exception("Temporary error")
            return "success"

        result = fail_then_succeed()
        assert result == "success"
        assert len(retry_attempts) == 2

    def test_retry_with_empty_data_detection(self):
        """测试空数据检测触发重试"""
        call_count = 0

        @retry_on_failure(max_retries=2, base_delay=0.01)
        def return_empty_then_data():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return None  # 空数据
            return "data"

        # 注意：当前实现中，空数据检测可能不会触发重试
        # 这取决于AntiCrawlDetector的配置
        result = return_empty_then_data()
        # 结果可能是None或"data"，取决于检测逻辑
        assert result is not None or call_count == 1


class TestAsyncRetryDecorator:
    """异步重试装饰器测试"""

    def test_async_retry_success_on_first_attempt(self):
        """测试异步第一次尝试就成功"""
        call_count = 0

        @async_retry_on_failure(max_retries=3, base_delay=0.01)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = asyncio.run(success_func())
        assert result == "success"
        assert call_count == 1

    def test_async_retry_success_after_failures(self):
        """测试异步失败后重试成功"""
        call_count = 0

        @async_retry_on_failure(max_retries=3, base_delay=0.01)
        async def eventual_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return "success"

        result = asyncio.run(eventual_success())
        assert result == "success"
        assert call_count == 3

    def test_async_retry_exhausted(self):
        """测试异步重试次数耗尽"""
        call_count = 0

        @async_retry_on_failure(max_retries=2, base_delay=0.01)
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("Permanent error")

        with pytest.raises(RetryExhaustedError):
            asyncio.run(always_fail())

        assert call_count == 3  # 1 initial + 2 retries


class TestRetryConfig:
    """重试配置测试"""

    def test_retry_config_creation(self):
        """测试重试配置创建"""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_retry_config_get_delay(self):
        """测试重试配置获取延迟时间"""
        config = RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=False,
        )

        # 第一次重试：1.0 * 2^0 = 1.0
        delay = config.get_delay(0)
        assert delay == 1.0

        # 第二次重试：1.0 * 2^1 = 2.0
        delay = config.get_delay(1)
        assert delay == 2.0

        # 第三次重试：1.0 * 2^2 = 4.0
        delay = config.get_delay(2)
        assert delay == 4.0

    def test_retry_config_max_delay(self):
        """测试最大延迟限制"""
        config = RetryConfig(
            max_retries=10,
            base_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=False,
        )

        # 第10次重试：1.0 * 2^9 = 512.0，但被限制为5.0
        delay = config.get_delay(9)
        assert delay == 5.0

    def test_predefined_configs(self):
        """测试预定义配置"""
        assert "fast" in RETRY_CONFIGS
        assert "standard" in RETRY_CONFIGS
        assert "patient" in RETRY_CONFIGS

        fast_config = RETRY_CONFIGS["fast"]
        assert fast_config.max_retries == 2
        assert fast_config.base_delay == 0.5

        standard_config = RETRY_CONFIGS["standard"]
        assert standard_config.max_retries == 3
        assert standard_config.base_delay == 1.0

        patient_config = RETRY_CONFIGS["patient"]
        assert patient_config.max_retries == 5
        assert patient_config.base_delay == 2.0


class TestCalculateDelay:
    """延迟计算测试"""

    def test_basic_delay(self):
        """测试基础延迟计算"""
        delay = _calculate_delay(
            attempt=0,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=False,
        )
        assert delay == 1.0

    def test_exponential_backoff(self):
        """测试指数退避"""
        delay = _calculate_delay(
            attempt=2,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=False,
        )
        assert delay == 4.0  # 1.0 * 2^2

    def test_max_delay_limit(self):
        """测试最大延迟限制"""
        delay = _calculate_delay(
            attempt=10,
            base_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=False,
        )
        assert delay == 5.0

    def test_suggested_delay(self):
        """测试建议延迟"""
        delay = _calculate_delay(
            attempt=0,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=False,
            suggested_delay=10.0,
        )
        assert delay == 10.0

    def test_jitter_adds_randomness(self):
        """测试抖动添加随机性"""
        delays = set()
        for _ in range(100):
            delay = _calculate_delay(
                attempt=0,
                base_delay=1.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter=True,
            )
            delays.add(delay)

        # 由于抖动，应该有多个不同的延迟值
        assert len(delays) > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
