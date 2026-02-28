from typing import Optional, Dict, Any


class SentinelDomainError(Exception):
    """
    Base domain-level exception for SentinelFlow.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "UNKNOWN",
        context: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
        original_exception: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.retryable = retryable
        self.original_exception = original_exception

    def __str__(self) -> str:
        base = self.message
        if self.error_code:
            base = f"[{self.error_code}] {base}"
        return base


class ConfigError(SentinelDomainError):
    """
    Fatal configuration error.
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "retryable" in kwargs:
            kwargs.pop("retryable")
        if "error_code" in kwargs:
            kwargs.pop("error_code")
            
        super().__init__(
            message,
            error_code="CONFIG_ERROR",
            retryable=False,
            **kwargs,
        )


class IngestionError(SentinelDomainError):
    """
    Raised when an ingestor fails.
    Often retryable.
    """

    def __init__(self, message: str, retryable: bool = True, error_code: str = "INGESTION_ERROR", **kwargs: Any) -> None:
        if "error_code" in kwargs:
            error_code = kwargs.pop("error_code")
            
        super().__init__(
            message,
            error_code=error_code,
            retryable=retryable,
            **kwargs,
        )


class DispatchError(SentinelDomainError):
    """
    Raised when a handler fails to dispatch.
    Often retryable.
    """

    def __init__(self, message: str, retryable: bool = False, **kwargs: Any) -> None:
        if "error_code" in kwargs:
            kwargs.pop("error_code")
            
        super().__init__(
            message,
            error_code="DISPATCH_ERROR",
            retryable=retryable,
            **kwargs,
        )