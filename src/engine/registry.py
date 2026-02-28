from typing import Dict, Type, Callable, Any, cast
from types import MappingProxyType

from src.interfaces.ingestor import BaseIngestor
from src.interfaces.evaluator import BaseEvaluator
from src.interfaces.handler import BaseHandler
from src.utils.exceptions import ConfigError

from src.core.evaluators.thresholds import ThresholdEvaluator
from src.core.evaluators.freshness import FreshnessEvaluator
from src.data.ingestors.http_api import HttpApiIngestor
from src.handlers.slack import SlackHandler


class Registry:
    """
    Stateful dependency registry.
    Maps configuration type strings to singletons.
    """
    _INSTANCES: Dict[str, Any] = {}

    _INGESTORS: Dict[str, Type[BaseIngestor[Any]]] = {
        "http_api": HttpApiIngestor,
    }

    _EVALUATORS: Dict[str, Type[BaseEvaluator[Any]]] = {
        "threshold": ThresholdEvaluator,
        "freshness": FreshnessEvaluator,
    }

    _HANDLERS: Dict[str, Type[BaseHandler[Any]]] = {
        "slack_webhook": SlackHandler,
    }

    # Make mappings immutable externally
    INGESTORS = MappingProxyType(_INGESTORS)
    EVALUATORS = MappingProxyType(_EVALUATORS)
    HANDLERS = MappingProxyType(_HANDLERS)

    @classmethod
    def get_ingestor(cls, name: str) -> BaseIngestor[Any]:
        if name not in cls._INGESTORS:
             raise ConfigError(f"Unknown ingestor type: {name}")
        if name not in cls._INSTANCES:
             cls._INSTANCES[name] = cls._INGESTORS[name]()
        return cast(BaseIngestor[Any], cls._INSTANCES[name])

    @classmethod
    def get_evaluator(cls, name: str) -> BaseEvaluator[Any]:
        if name not in cls._EVALUATORS:
             raise ConfigError(f"Unknown evaluator type: {name}")
        if name not in cls._INSTANCES:
             cls._INSTANCES[name] = cls._EVALUATORS[name]()
        return cast(BaseEvaluator[Any], cls._INSTANCES[name])

    @classmethod
    def get_handler(cls, name: str) -> BaseHandler[Any]:
        if name not in cls._HANDLERS:
             raise ConfigError(f"Unknown handler type: {name}")
        if name not in cls._INSTANCES:
             cls._INSTANCES[name] = cls._HANDLERS[name]()
        return cast(BaseHandler[Any], cls._INSTANCES[name])

    @classmethod
    def register_ingestor(cls, name: str, implementation: Type[BaseIngestor[Any]]) -> None:
        if not issubclass(implementation, BaseIngestor):
            raise TypeError("Ingestor must inherit from BaseIngestor")
        cls._INGESTORS[name] = implementation

    @classmethod
    def register_evaluator(cls, name: str, implementation: Type[BaseEvaluator[Any]]) -> None:
        if not issubclass(implementation, BaseEvaluator):
            raise TypeError("Evaluator must inherit from BaseEvaluator")
        cls._EVALUATORS[name] = implementation

    @classmethod
    def register_handler(cls, name: str, implementation: Type[BaseHandler[Any]]) -> None:
        if not issubclass(implementation, BaseHandler):
            raise TypeError("Handler must inherit from BaseHandler")
        cls._HANDLERS[name] = implementation