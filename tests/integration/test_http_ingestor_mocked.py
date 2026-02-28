"""Tests for HttpApiIngestor with mocked aiohttp sessions."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Any, Dict

from src.data.ingestors.http_api import HttpApiIngestor
from src.utils.exceptions import IngestionError


@pytest.fixture
def ingestor() -> HttpApiIngestor:
    return HttpApiIngestor()


@pytest.fixture
def base_config() -> Dict[str, Any]:
    return {
        "url": "http://api.dummy.local/metrics",
        "method": "GET",
        "timeout_seconds": 2.0,
    }


@pytest.mark.asyncio
async def test_http_ingestor_success(
    ingestor: HttpApiIngestor, base_config: Dict[str, Any]
) -> None:
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json = AsyncMock(return_value={"value": 42.5})
    mock_response.raise_for_status = MagicMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = AsyncMock()
    mock_session.request = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        payload = await ingestor.fetch("test_metric", base_config)
        assert payload.raw_data == {"value": 42.5}
        assert payload.metric_id == "test_metric"


@pytest.mark.asyncio
async def test_http_ingestor_missing_url(ingestor: HttpApiIngestor) -> None:
    config: Dict[str, Any] = {"method": "GET"}

    with pytest.raises(IngestionError, match="Missing 'url'"):
        await ingestor.fetch("test_metric", config)


@pytest.mark.asyncio
async def test_http_ingestor_network_error(
    ingestor: HttpApiIngestor, base_config: Dict[str, Any]
) -> None:
    import aiohttp

    mock_session = AsyncMock()
    mock_session.request = MagicMock(side_effect=aiohttp.ClientError("DNS failure"))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(IngestionError) as exc_info:
            await ingestor.fetch("test_metric", base_config)
        assert exc_info.value.retryable is True
