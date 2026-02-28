from typing import Callable, TypeVar, Awaitable, ParamSpec, cast, Any
import random
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
    RetryCallState,
)

from aiohttp import ClientError
from src.utils.exceptions import SentinelDomainError


P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def _is_retryable_exception(exc: BaseException) -> bool:
    if isinstance(exc, ClientError):
        return True
    if isinstance(exc, SentinelDomainError):
        return getattr(exc, "retryable", False)
    return False


def _exponential_with_jitter(
    multiplier: float,
    max_delay: float,
) -> Callable[[RetryCallState], float]:

    base_wait = wait_exponential(multiplier=multiplier, max=max_delay)

    def _wait_with_jitter(retry_state: RetryCallState) -> float:
        delay = base_wait(retry_state)
        jitter = random.uniform(0.0, delay * 0.2)
        return delay + jitter

    return _wait_with_jitter


def async_retry_network(
    max_attempts: int = 3,
    max_delay: float = 10.0,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:

    def decorator(
        fn: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R]]:

        def before_sleep(retry_state: RetryCallState) -> None:
            if retry_state.outcome is not None and retry_state.outcome.failed:
                exc = retry_state.outcome.exception()
                sleep_time = getattr(retry_state.next_action, "sleep", 0)
                logger.warning(
                    f"Retrying {fn.__module__}.{fn.__qualname__} in {sleep_time} seconds "
                    f"as it raised {exc.__class__.__name__}: {exc}."
                )

        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=_exponential_with_jitter(1.0, max_delay),
            retry=retry_if_exception(_is_retryable_exception),
            before_sleep=before_sleep,
            reraise=True,
        )(fn)

    return decorator