"""
数据源回退机制模块
当主数据源（AKShare）失败时，自动切换到备用数据源
"""
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DataSourcePriority(Enum):
    """数据源优先级"""
    PRIMARY = 1  # 主数据源
    SECONDARY = 2  # 备用数据源
    TERTIARY = 3  # 第三数据源
    FALLBACK = 4  # 兜底数据源


@dataclass
class DataSourceConfig:
    """数据源配置"""
    name: str
    priority: DataSourcePriority
    fetch_func: Callable[..., Any]
    available: bool = True
    error_count: int = 0
    max_errors: int = 5  # 最大错误次数，超过后标记为不可用
    last_error: Optional[str] = None


class DataSourceFallback:
    """
    数据源回退管理器
    支持多个数据源的自动切换和故障转移
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._sources: Dict[str, DataSourceConfig] = {}
        self._fallback_order: List[str] = []

    def add_source(
        self,
        name: str,
        fetch_func: Callable,
        priority: DataSourcePriority = DataSourcePriority.SECONDARY,
        max_errors: int = 5,
    ) -> None:
        """
        添加数据源

        Args:
            name: 数据源名称
            fetch_func: 数据获取函数
            priority: 优先级
            max_errors: 最大错误次数，超过后标记为不可用
        """
        self._sources[name] = DataSourceConfig(
            name=name,
            priority=priority,
            fetch_func=fetch_func,
            max_errors=max_errors,
        )
        self._update_fallback_order()

    def _update_fallback_order(self) -> None:
        """更新回退顺序（按优先级排序）"""
        self._fallback_order = sorted(
            self._sources.keys(),
            key=lambda x: self._sources[x].priority.value,
        )

    def get_available_sources(self) -> List[str]:
        """获取可用数据源列表"""
        return [
            name for name in self._fallback_order
            if self._sources[name].available
        ]

    def mark_error(self, source_name: str, error: str) -> None:
        """
        标记数据源错误

        Args:
            source_name: 数据源名称
            error: 错误信息
        """
        if source_name in self._sources:
            source = self._sources[source_name]
            source.error_count += 1
            source.last_error = error

            if source.error_count >= source.max_errors:
                source.available = False
                logger.warning(
                    f"⚠️ 数据源 {source_name} 错误次数过多 ({source.error_count}), "
                    f"已标记为不可用"
                )

    def mark_success(self, source_name: str) -> None:
        """
        标记数据源成功（重置错误计数）

        Args:
            source_name: 数据源名称
        """
        if source_name in self._sources:
            source = self._sources[source_name]
            source.error_count = 0
            source.last_error = None
            source.available = True

    def reset_all(self) -> None:
        """重置所有数据源状态"""
        for source in self._sources.values():
            source.error_count = 0
            source.last_error = None
            source.available = True

    def fetch_with_fallback(
        self,
        *args,
        preferred_source: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        使用回退机制获取数据

        Args:
            *args: 传递给数据获取函数的参数
            preferred_source: 首选数据源（可选）
            **kwargs: 传递给数据获取函数的关键字参数

        Returns:
            获取到的数据

        Raises:
            Exception: 所有数据源都失败时抛出最后一个异常
        """
        sources_to_try = self._fallback_order.copy()

        # 如果指定了首选数据源，将其放在最前面
        if preferred_source and preferred_source in sources_to_try:
            sources_to_try.remove(preferred_source)
            sources_to_try.insert(0, preferred_source)

        last_exception = None
        for source_name in sources_to_try:
            source = self._sources[source_name]
            if not source.available:
                continue

            try:
                logger.debug(f"📊 尝试使用数据源: {source_name}")
                result = source.fetch_func(*args, **kwargs)

                # 检查结果是否有效
                if result is not None:
                    self.mark_success(source_name)
                    logger.debug(f"✅ 数据源 {source_name} 获取成功")
                    return result
                else:
                    logger.debug(f"⚠️ 数据源 {source_name} 返回空数据")

            except Exception as e:
                last_exception = e
                self.mark_error(source_name, str(e))
                logger.warning(f"⚠️ 数据源 {source_name} 失败: {e}")

        # 所有数据源都失败
        available_sources = self.get_available_sources()
        if not available_sources:
            logger.error(f"❌ 所有数据源都不可用")
        else:
            logger.error(f"❌ 所有可用数据源都失败")

        if last_exception:
            raise last_exception
        return None

    async def async_fetch_with_fallback(
        self,
        *args,
        preferred_source: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        使用回退机制获取数据（异步版本）

        Args:
            *args: 传递给数据获取函数的参数
            preferred_source: 首选数据源（可选）
            **kwargs: 传递给数据获取函数的关键字参数

        Returns:
            获取到的数据

        Raises:
            Exception: 所有数据源都失败时抛出最后一个异常
        """
        sources_to_try = self._fallback_order.copy()

        # 如果指定了首选数据源，将其放在最前面
        if preferred_source and preferred_source in sources_to_try:
            sources_to_try.remove(preferred_source)
            sources_to_try.insert(0, preferred_source)

        last_exception = None
        for source_name in sources_to_try:
            source = self._sources[source_name]
            if not source.available:
                continue

            try:
                logger.debug(f"📊 尝试使用数据源: {source_name}")
                result = await source.fetch_func(*args, **kwargs)

                # 检查结果是否有效
                if result is not None:
                    self.mark_success(source_name)
                    logger.debug(f"✅ 数据源 {source_name} 获取成功")
                    return result
                else:
                    logger.debug(f"⚠️ 数据源 {source_name} 返回空数据")

            except Exception as e:
                last_exception = e
                self.mark_error(source_name, str(e))
                logger.warning(f"⚠️ 数据源 {source_name} 失败: {e}")

        # 所有数据源都失败
        available_sources = self.get_available_sources()
        if not available_sources:
            logger.error(f"❌ 所有数据源都不可用")
        else:
            logger.error(f"❌ 所有可用数据源都失败")

        if last_exception:
            raise last_exception
        return None

    def get_status(self) -> Dict[str, Any]:
        """获取数据源状态信息"""
        return {
            "name": self.name,
            "sources": {
                name: {
                    "available": source.available,
                    "error_count": source.error_count,
                    "last_error": source.last_error,
                    "priority": source.priority.name,
                }
                for name, source in self._sources.items()
            },
            "available_sources": self.get_available_sources(),
        }


# 预定义的回退配置
class StockQuotesFallback(DataSourceFallback):
    """股票行情数据源回退"""

    def __init__(self):
        super().__init__("stock_quotes")
        # 数据源将在使用时动态添加


class StockNewsFallback(DataSourceFallback):
    """股票新闻数据源回退"""

    def __init__(self):
        super().__init__("stock_news")
        # 数据源将在使用时动态添加


class StockListFallback(DataSourceFallback):
    """股票列表数据源回退"""

    def __init__(self):
        super().__init__("stock_list")
        # 数据源将在使用时动态添加
