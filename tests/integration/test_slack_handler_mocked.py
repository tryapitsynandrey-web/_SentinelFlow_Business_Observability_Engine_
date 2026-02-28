"""Tests for SlackHandler with mocked aiohttp sessions."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Any, Dict
from datetime import datetime, timezone

from src.handlers.slack import SlackHandler
from src.models.entities import AlertEvent
from src.utils.exceptions import DispatchError


@pytest.fixture
def mock_alert() -> AlertEvent:
    return AlertEvent(
        metric_id="test_slack",
        evaluator_type="test",
        severity="critical",
        message="Test webhook",
        timestamp=datetime.now(timezone.utc),
        context={"value": 100.0},
    )


@pytest.fixture
def handler_config() -> Dict[str, Any]:
    return {"webhook_url_env_key": "slack_webhook_url"}


@pytest.mark.asyncio
async def test_slack_handler_success(
    handler_config: Dict[str, Any], mock_alert: AlertEvent, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/mock")
    # Clear the lru_cache so the new env var is picked up
    from src.config.settings import get_settings
    get_settings.cache_clear()

    handler = SlackHandler()

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    # Patch the handler's internal session
    handler._session = mock_session

    await handler.dispatch(mock_alert, handler_config)


@pytest.mark.asyncio
async def test_slack_handler_missing_webhook(
    mock_alert: AlertEvent, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    from src.config.settings import get_settings
    get_settings.cache_clear()

    handler = SlackHandler()
    config: Dict[str, Any] = {"webhook_url_env_key": "slack_webhook_url"}

    with pytest.raises(DispatchError, match="not configured"):
        await handler.dispatch(mock_alert, config)


@pytest.mark.asyncio
async def test_slack_handler_network_error(
    handler_config: Dict[str, Any], mock_alert: AlertEvent, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/mock")
    from src.config.settings import get_settings
    get_settings.cache_clear()

    handler = SlackHandler()

    import aiohttp

    mock_session = AsyncMock()
    mock_session.post = MagicMock(side_effect=aiohttp.ClientError("Connection reset"))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    handler._session = mock_session

    with pytest.raises(DispatchError, match="Network error"):
        await handler.dispatch(mock_alert, handler_config)
