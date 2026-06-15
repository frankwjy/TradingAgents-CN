"""
请求ID/Trace-ID 中间件
- 为每个请求生成唯一 ID（trace_id），写入 request.state 与响应头
- 将 trace_id 写入 logging 的 contextvars，使所有日志自动带出
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging_context import clear_request_context, set_request_context, trace_id_var

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求ID和日志中间件（trace_id）"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID/trace_id
        trace_id = str(uuid.uuid4())
        request.state.request_id = trace_id  # 兼容现有字段名
        request.state.trace_id = trace_id

        # 将 trace_id 写入 contextvars
        token = trace_id_var.set(trace_id)

        # Set structured request context
        client_ip = request.client.host if request.client else "unknown"
        ctx_token = set_request_context(
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
        )

        # 记录请求开始时间
        start_time = time.time()

        # 记录请求信息 (structured via extra fields)
        logger.info(
            "request_started", extra={"method": request.method, "path": request.url.path, "client_ip": client_ip}
        )

        try:
            # 处理请求
            response = await call_next(request)

            # 计算处理时间
            process_time = time.time() - start_time

            # 添加响应头
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Request-ID"] = trace_id  # 兼容
            response.headers["X-Process-Time"] = f"{process_time:.3f}"

            # 记录请求完成信息
            status_class = (
                "success"
                if response.status_code < 400
                else "client_error"
                if response.status_code < 500
                else "server_error"
            )
            logger.info(
                "request_completed",
                extra={
                    "status_code": response.status_code,
                    "status_class": status_class,
                    "duration_s": round(process_time, 3),
                },
            )

            return response

        except Exception as exc:
            # 计算处理时间
            process_time = time.time() - start_time

            # 记录请求异常信息
            logger.error(
                "request_failed", extra={"duration_s": round(process_time, 3), "error": str(exc)}, exc_info=True
            )
            raise

        finally:
            # 清理 contextvar，避免泄露到后续请求
            try:
                clear_request_context(ctx_token)
                trace_id_var.reset(token)
            except Exception:
                pass
