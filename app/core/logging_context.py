import contextvars
import logging
from typing import Optional

# Shared contextvar for trace id across the whole process
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")

# Additional request-scoped context for structured logging
request_context_var: contextvars.ContextVar[dict] = contextvars.ContextVar("request_context")


def set_request_context(**kwargs) -> contextvars.Token:
    """Set additional request-scoped context fields (method, path, user_id, etc.)."""
    return request_context_var.set(kwargs)


def clear_request_context(token: contextvars.Token | None = None) -> None:
    """Clear request-scoped context."""
    if token:
        request_context_var.reset(token)
    else:
        request_context_var.set({})


class LoggingContextFilter(logging.Filter):
    """Injects trace_id and request context from contextvars into LogRecord.
    Always sets record.trace_id to a string (default '-') so formatters are safe.
    Also injects any additional request_context fields as record attributes.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.trace_id = trace_id_var.get()
        except Exception:
            record.trace_id = "-"

        # Inject request context fields into log record
        try:
            ctx = request_context_var.get(None)
            if ctx:
                for key, value in ctx.items():
                    if not hasattr(record, key):
                        setattr(record, key, value)
        except LookupError:
            pass

        return True
