#!/usr/bin/env python3
"""
SingleFlight 模块
防止缓存击穿：同一缓存键的并发请求只执行一次实际加载，其余等待并共享结果。
"""

import asyncio
import threading
from typing import Any, Callable, Dict, Optional, Tuple


class SingleFlight:
    """同步版 SingleFlight：同一 key 只执行一次回调，其余调用者阻塞等待结果。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._in_flight: Dict[str, Tuple[threading.Event, list]] = {}

    def do(self, key: str, fn: Callable[[], Any]) -> Any:
        """
        执行 fn，但如果 key 已有在途请求则等待其结果。

        Args:
            key: 缓存键
            fn: 无参回调，返回要缓存的值

        Returns:
            fn 的返回值

        Raises:
            如果在途请求失败，等待者也会收到相同的异常
        """
        with self._lock:
            if key in self._in_flight:
                event, result_box = self._in_flight[key]
                # 有在途请求，等待
                waiting = True
            else:
                # 首个请求，注册自己
                event = threading.Event()
                result_box = [None, None, False]  # [result, error, has_error]
                self._in_flight[key] = (event, result_box)
                waiting = False

        if waiting:
            event.wait()
            if result_box[2]:
                raise result_box[1]
            return result_box[0]

        # 执行实际加载
        try:
            result = fn()
            result_box[0] = result
        except Exception as e:
            result_box[1] = e
            result_box[2] = True
            raise
        finally:
            # 通知所有等待者
            event.set()
            with self._lock:
                self._in_flight.pop(key, None)

        return result


class AsyncSingleFlight:
    """异步版 SingleFlight：同一 key 只执行一次协程，其余 await 共享结果。"""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._in_flight: Dict[str, Tuple[asyncio.Event, list]] = {}

    async def do(self, key: str, fn: Callable[[], Any]) -> Any:
        """
        异步执行 fn，但如果 key 已有在途请求则等待其结果。

        Args:
            key: 缓存键
            fn: 无参回调（可以是协程或普通函数）

        Returns:
            fn 的返回值
        """
        async with self._lock:
            if key in self._in_flight:
                event, result_box = self._in_flight[key]
                waiting = True
            else:
                event = asyncio.Event()
                result_box = [None, None, False]
                self._in_flight[key] = (event, result_box)
                waiting = False

        if waiting:
            await event.wait()
            if result_box[2]:
                raise result_box[1]
            return result_box[0]

        try:
            if asyncio.iscoroutinefunction(fn):
                result = await fn()
            else:
                result = fn()
            result_box[0] = result
        except Exception as e:
            result_box[1] = e
            result_box[2] = True
            raise
        finally:
            event.set()
            async with self._lock:
                self._in_flight.pop(key, None)

        return result
