import yaml
from typing import Any, Dict, List, Literal, Union, Annotated

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    AnyHttpUrl,
    model_validator,
    ConfigDict,
)

from src.utils.exceptions import ConfigError
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# Base Config Behavior
# ============================================================

class StrictBaseModel(BaseModel):
    """
    Base model with strict validation behavior:
    - Forbids unknown fields
    - Ensures schema discipline
    """
    model_config = ConfigDict(extra="forbid")


# ============================================================
# Sub-Models
# ============================================================

class ObservabilityConfig(StrictBaseModel):
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    service_name: str = "sentinelflow"
    otlp_endpoint: str = "http://localhost:4317"
    metrics_port: int = Field(default=9108, gt=0, lt=65536)
    admin_port: int = Field(default=9109, gt=0, lt=65536)

class CircuitBreakerConfig(StrictBaseModel):
    enabled: bool = True
    failure_threshold: int = Field(default=5, gt=0)
    reset_timeout_seconds: int = Field(default=30, gt=0)

class CheckResilienceConfig(StrictBaseModel):
    timeout_seconds: float = Field(default=15.0, gt=0)
    max_inflight: int = Field(default=10, gt=0)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)

class GlobalConfig(StrictBaseModel):
    concurrency_limit: int = Field(default=10, ge=1, le=100)
    default_timeout_seconds: float = Field(default=15.0, gt=0)
    scheduler_mode: Literal["run_once", "daemon"] = "run_once"
    interval_seconds: int = Field(default=60, ge=1)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)


class HttpIngestorConfig(StrictBaseModel):
    type: Literal["http_api"]
    url: AnyHttpUrl
    method: Literal["GET", "POST"] = "GET"
    json_path: str | None = None


class ThresholdEvaluatorConfig(StrictBaseModel):
    type: Literal["threshold"]
    operator: Literal["<", "<=", ">", ">=", "between"]
    value: Union[float, int, List[float]]
    severity: Literal["low", "medium", "high", "critical"] = "high"

    @model_validator(mode="after")
    def validate_between_operator(self) -> "ThresholdEvaluatorConfig":
        if self.operator == "between":
            if not isinstance(self.value, list) or len(self.value) != 2:
                raise ValueError(
                    "For 'between' operator, value must be a list of exactly two numbers."
                )
        return self


class FreshnessEvaluatorConfig(StrictBaseModel):
    type: Literal["freshness"]
    max_age_seconds: int = Field(gt=0)
    severity: Literal["low", "medium", "high", "critical"] = "medium"


class AlertPolicyConfig(StrictBaseModel):
    cooldown_seconds: int = Field(default=300, ge=0)
    dedupe_window_seconds: int = Field(default=3600, ge=0)
    severity: Literal["low", "medium", "high", "critical"] = "high"


class SlackHandlerConfig(StrictBaseModel):
    type: Literal["slack_webhook"]
    webhook_url_env_key: str

    @model_validator(mode="after")
    def validate_env_key(self) -> "SlackHandlerConfig":
        if not self.webhook_url_env_key.strip():
            raise ValueError("webhook_url_env_key cannot be empty.")
        return self


# ============================================================
# Discriminated Unions (Deterministic Polymorphism)
# ============================================================

EvaluatorConfig = Annotated[
    Union[ThresholdEvaluatorConfig, FreshnessEvaluatorConfig],
    Field(discriminator="type"),
]

IngestorConfig = Annotated[
    HttpIngestorConfig,
    Field(discriminator="type"),
]

HandlerConfig = Annotated[
    SlackHandlerConfig,
    Field(discriminator="type"),
]


# ============================================================
# Unified Models
# ============================================================

class MetricCheckConfig(StrictBaseModel):
    metric_id: str

    ingestor: IngestorConfig

    evaluators: List[EvaluatorConfig] = Field(min_length=1)

    alert_policy: AlertPolicyConfig = Field(default_factory=AlertPolicyConfig)

    handlers: List[HandlerConfig] = Field(min_length=1)
    
    resilience: CheckResilienceConfig = Field(default_factory=CheckResilienceConfig)


class AppConfig(StrictBaseModel):
    global_config: GlobalConfig = Field(
        default_factory=GlobalConfig,
        alias="global",
    )
    checks: List[MetricCheckConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_registry_types(self) -> "AppConfig":
        from src.engine.registry import Registry
        for check in self.checks:
            try:
                Registry.get_ingestor(check.ingestor.type)
            except ConfigError as exc:
                raise ValueError(str(exc))
                
            for eval_cfg in check.evaluators:
                try:
                    Registry.get_evaluator(eval_cfg.type)
                except ConfigError as exc:
                    raise ValueError(str(exc))
                    
            for handler_cfg in check.handlers:
                try:
                    Registry.get_handler(handler_cfg.type)
                except ConfigError as exc:
                    raise ValueError(str(exc))
        return self


# ============================================================
# Loader
# ============================================================

def load_config(file_path: str) -> AppConfig:
    """
    Parses and strictly validates a YAML configuration file
    against the AppConfig schema.

    Returns:
        AppConfig — fully validated configuration object

    Raises:
        ConfigError — if file missing, invalid YAML, or schema invalid.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)

        if not raw_data:
            raise ConfigError(f"Configuration file '{file_path}' is empty.")

        validated_config = AppConfig(**raw_data)

        logger.info(
            f"Loaded and validated {len(validated_config.checks)} checks from {file_path}"
        )

        return validated_config

    except FileNotFoundError:
        raise ConfigError(f"Configuration file not found at '{file_path}'")

    except yaml.YAMLError as e:
        raise ConfigError(
            f"Failed to parse YAML syntax in '{file_path}': {e}"
        )

    except ValidationError as e:
        raise ConfigError(
            f"Configuration schema validation failed:\n{e.json(indent=2)}"
        )