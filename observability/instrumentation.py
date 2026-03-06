import time
from typing import Callable, Any, TypeVar, Coroutine, ParamSpec, Awaitable
from functools import wraps

from observability.metrics import (
    CHECK_DURATION,
    CHECK_FAILURES,
    DISPATCH_FAILURES,
    ACTIVE_CHECKS,
)
from observability.tracing import get_tracer

P = ParamSpec("P")
T = TypeVar("T")

def instrument_check_execution(check_id: str) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            tracer = get_tracer()
            ACTIVE_CHECKS.inc()
            start_time = time.perf_counter()
            with tracer.start_as_current_span(f"check_execution_{check_id}") as span:
                span.set_attribute("check.id", check_id)
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    CHECK_FAILURES.labels(check_id=check_id).inc()
                    raise
                finally:
                    duration = time.perf_counter() - start_time
                    CHECK_DURATION.labels(check_id=check_id).observe(duration)
                    ACTIVE_CHECKS.dec()
        return wrapper
    return decorator

def instrument_dispatch(handler_type: str) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            tracer = get_tracer()
            with tracer.start_as_current_span(f"dispatch_{handler_type}") as span:
                span.set_attribute("handler.type", handler_type)
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    DISPATCH_FAILURES.labels(handler_type=handler_type).inc()
                    raise
        return wrapper
    return decorator
