import pytest
from typing import Any

from src.engine.registry import Registry
from src.interfaces.ingestor import BaseIngestor
from src.interfaces.evaluator import BaseEvaluator
from src.interfaces.handler import BaseHandler
from src.utils.exceptions import ConfigError
from tests.fixtures.dummy import DummyIngestor, DummyEvaluator, DummyHandler

def test_registry_register_and_get_ingestor():
    # Arrange
    Registry.register_ingestor("dummy_test", DummyIngestor)
    
    # Act
    instance = Registry.get_ingestor("dummy_test")
    
    # Assert
    assert isinstance(instance, DummyIngestor)

def test_registry_get_unknown_ingestor():
    with pytest.raises(ConfigError) as exc_info:
        Registry.get_ingestor("unknown_type")
    assert "Unknown ingestor type: unknown_type" in str(exc_info.value)

def test_registry_register_invalid_ingestor():
    class NotAnIngestor:
        pass

    with pytest.raises(TypeError) as exc_info:
        Registry.register_ingestor("invalid", NotAnIngestor) # type: ignore
    assert "Ingestor must inherit from BaseIngestor" in str(exc_info.value)

def test_registry_evaluator_lifecycle():
    Registry.register_evaluator("dummy_eval", DummyEvaluator)
    instance = Registry.get_evaluator("dummy_eval")
    assert isinstance(instance, DummyEvaluator)

    with pytest.raises(ConfigError):
        Registry.get_evaluator("not_an_evaluator")

def test_registry_handler_lifecycle():
    Registry.register_handler("dummy_handler", DummyHandler)
    instance = Registry.get_handler("dummy_handler")
    assert isinstance(instance, DummyHandler)

    with pytest.raises(ConfigError):
        Registry.get_handler("not_a_handler")

def test_registry_singleton_behavior():
    Registry.register_ingestor("singleton_test", DummyIngestor)
    instance1 = Registry.get_ingestor("singleton_test")
    instance2 = Registry.get_ingestor("singleton_test")
    assert instance1 is instance2
