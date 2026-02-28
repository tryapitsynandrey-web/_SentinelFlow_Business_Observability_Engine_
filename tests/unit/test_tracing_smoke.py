import pytest
import asyncio
from opentelemetry import trace

from observability.tracing import configure_tracing, get_tracer
from observability.context import span

@pytest.fixture(autouse=True)
def setup_tracing():
    # Smoke test enablement
    configure_tracing("sentinel-test", "http://localhost:4317")

def test_tracer_returns_valid_instance():
    tracer = get_tracer()
    assert tracer is not None

@pytest.mark.asyncio
async def test_tracing_context_manager_smoke():
    async with span("test_span", test_attr="value") as s:
        # Span is active
        assert s is not None
        assert s.is_recording()

@pytest.mark.asyncio
async def test_tracing_async_context():
    async def traced_op():
        async with span("async_span"):
            await asyncio.sleep(0.01)
            return True
            
    res = await traced_op()
    assert res is True
