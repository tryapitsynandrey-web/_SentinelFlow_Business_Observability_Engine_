from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any
from observability.tracing import get_tracer

@asynccontextmanager
async def span(name: str, **attrs: Any) -> AsyncGenerator[Any, None]:
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as trace_span:
        for k, v in attrs.items():
            if v is not None:
                trace_span.set_attribute(k, v)
        yield trace_span
