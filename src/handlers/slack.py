import aiohttp
from typing import Any, Dict, Optional, Awaitable

from src.interfaces.handler import BaseHandler
from src.models.entities import AlertEvent
from src.utils.retry import async_retry_network
from src.utils.exceptions import DispatchError
from src.config.settings import get_settings
from src.utils.logger import get_logger
from resilience.circuit_breaker import CircuitBreaker
from observability.context import span
from observability.metrics import Metrics

logger = get_logger(__name__)


class SlackHandler(BaseHandler[Dict[str, Any]]):
    """
    Production-grade Slack webhook dispatcher.
    """

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        # Add circuit breaker for resilience
        self._breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=10)
            connector = aiohttp.TCPConnector(limit=50)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
            )
        return self._session

    # 👇 override теперь совпадает по типу
    def shutdown(self) -> Awaitable[None]:
        async def _close() -> None:
            if self._session and not self._session.closed:
                await self._session.close()

        return _close()

    def _build_slack_payload(self, event: AlertEvent) -> Dict[str, Any]:
        return {
            "text": f"*{event.severity.upper()} Alert:* {event.metric_id}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 {event.severity.upper()} Alert: {event.metric_id}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": event.message,
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": (
                                f"Evaluator: `{event.evaluator_type}` | "
                                f"Time: {event.timestamp.isoformat()}"
                            ),
                        }
                    ],
                },
            ],
        }

    @async_retry_network(max_attempts=3, max_delay=10.0)
    async def dispatch(
        self,
        event: AlertEvent,
        config: Dict[str, Any],
    ) -> None:
        """
        Sends a formatted message to Slack. Retries on network errors.
        Circuit breaker protected.
        """
        if not await self._breaker.allow_request():
            logger.warning("Circuit breaker OPEN. Skipping Slack dispatch.")
            return

        webhook_env_key = config.get("webhook_url_env_key")
        if not webhook_env_key:
            raise DispatchError("Missing webhook_url_env_key in Slack handler config", retryable=False, error_code="MISSING_WEBHOOK")

        settings = get_settings()
        webhook_url = getattr(settings, webhook_env_key.lower(), None)

        if not webhook_url:
            raise DispatchError(
                f"Slack webhook not configured for env key '{webhook_env_key}'",
                retryable=False,
                error_code="MISSING_WEBHOOK"
            )
            
        webhook_url_str = str(webhook_url)

        payload = self._build_slack_payload(event)
        session = await self._get_session()

        try:
            import time
            metrics = Metrics()
            d_start = time.perf_counter()
            async with span(
                "slack.dispatch",
                check_id=event.metric_id,
                severity=event.severity,
                host=webhook_url_str.split("/")[2] if "//" in webhook_url_str else webhook_url_str
            ):
                async with session.post(
                    webhook_url_str,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    response.raise_for_status()
                    
            metrics.observe_dispatch(event.metric_id, "slack_webhook", time.perf_counter() - d_start)

            await self._breaker.record_success()
            logger.info(
                "Successfully dispatched alert to Slack.",
                extra={"metric_id": event.metric_id, "severity": event.severity},
            )

        except aiohttp.ClientError as exc:
            await self._breaker.record_failure()
            raise DispatchError(
                f"Network error during Slack dispatch: {exc}", retryable=True
            ) from exc