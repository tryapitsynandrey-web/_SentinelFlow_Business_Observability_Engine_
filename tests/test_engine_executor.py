import pytest
import asyncio
from src.engine.executor import Executor
from src.core.policies import AlertPolicy

# We need to simulate a slow task using monkeypatch
class MockIngestor:
    async def fetch(self, metric_id, config):
        await asyncio.sleep(0.1) # Simulate slow network
        
class MockEvaluator:
    def evaluate(self, payload, config):
        return None
        
class MockRegistry:
    @classmethod
    def get_ingestor(cls, name):
         return MockIngestor()
         
    @classmethod
    def get_evaluator(cls, name):
         return MockEvaluator()

@pytest.mark.asyncio
async def test_bounded_concurrency(monkeypatch):
    # Monkeypatch the Registry inside executor
    monkeypatch.setattr("src.engine.executor.Registry", MockRegistry)
    
    # Set limit to 2
    policy = AlertPolicy()
    executor = Executor(concurrency_limit=2, policy=policy)
    
    config = {
        "global": {"default_timeout_seconds": 1.0},
        "checks": [{"metric_id": f"test_{i}"} for i in range(10)]
    }
    
    start_time = asyncio.get_event_loop().time()
    await executor.execute_batch(config)
    end_time = asyncio.get_event_loop().time()
    
    duration = end_time - start_time
    
    # 10 tasks, concurrency 2, each takes 0.1s => ~0.5 seconds minimum
    assert duration >= 0.5
    assert duration < 1.0 # Should not take 1 full second if concurrent
