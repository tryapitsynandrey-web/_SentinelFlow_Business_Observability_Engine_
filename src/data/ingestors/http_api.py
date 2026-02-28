import aiohttp
from datetime import datetime, timezone
from typing import Any, Dict
from src.interfaces.ingestor import BaseIngestor
from src.models.entities import MetricPayload
from src.utils.retry import async_retry_network
from src.utils.exceptions import IngestionError
from observability.context import span
from observability.metrics import Metrics
from urllib.parse import urlparse


class HttpApiIngestor(BaseIngestor[Dict[str, Any]]):
    """
    Ingests data by making an asynchronous HTTP request to a public API.
    """

    def _extract_value(self, json_data: Dict[str, Any], path: str) -> Any:
        """
        Extracts a nested value from a JSON dict using dot notation.
        """
        if not path:
             return None
             
        # Support dot notation like "data.count"
        keys = path.split('.')
        current: Any = json_data
        
        try:
            for key in keys:
                 if isinstance(current, dict):
                      current = current.get(key)
                 elif isinstance(current, list):
                      try:
                          idx = int(key)
                          current = current[idx]
                      except (ValueError, IndexError):
                          return None
                 else:
                      return None
        except (KeyError, TypeError, ValueError, Exception):
             return None
             
        return current

    @async_retry_network(max_attempts=3, max_delay=10.0)
    async def fetch(self, metric_id: str, config: Dict[str, Any]) -> MetricPayload:
        """
        Fetches the JSON payload and normalizes it into a MetricPayload.
        """
        url_raw = config.get("url")
        if not url_raw:
            raise IngestionError("Missing 'url' in HttpApiIngestor config", retryable=False)
        url = str(url_raw)
        parsed_url = urlparse(url)
        host = parsed_url.hostname or "unknown"

        method_raw = config.get("method", "GET")
        if not isinstance(method_raw, str):
            raise IngestionError("'method' must be a string", retryable=False)
        method = method_raw.upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}:
            raise IngestionError(f"Invalid HTTP method: {method}", retryable=False)

        json_path = config.get("json_path")
        if json_path is not None and not isinstance(json_path, str):
            raise IngestionError("'json_path' must be a string", retryable=False)

        allow_non_json = bool(config.get("allow_non_json", False))
        
        timeout_sec_raw = config.get("timeout_seconds", 10.0)
        try:
            timeout_sec = float(timeout_sec_raw)
        except (ValueError, TypeError):
            timeout_sec = 10.0
            
        client_timeout = aiohttp.ClientTimeout(total=timeout_sec)

        try:
            metrics = Metrics()
            async with span("http.request", host=host, method=method):
                async with aiohttp.ClientSession(timeout=client_timeout) as session:
                    async with session.request(method, url) as response:
                        status_class = f"{response.status // 100}xx"
                        
                        try:
                            metrics.inc_http_request(
                                check_id=metric_id, host=host, method=method, status_class=status_class
                            )
                        except Exception:
                            pass
                            
                        response.raise_for_status() 
                        
                        # Validate Content-Type
                        content_type = response.headers.get("Content-Type", "").lower()
                        is_json = "application/json" in content_type
                        
                        if json_path and not is_json:
                            raise IngestionError(
                                f"Value extraction requires JSON payload but got Content-Type: {content_type}",
                                retryable=False,
                                error_code="BAD_CONTENT_TYPE"
                            )
                        
                        if not is_json:
                            text_data = await response.text()
                            return MetricPayload(
                                 metric_id=metric_id,
                                 timestamp=datetime.now(timezone.utc),
                                 value=None,
                                 raw_data={"text": text_data}
                            )
                        
                        try:
                            data = await response.json()
                        except aiohttp.ContentTypeError as exc:
                            text = await response.text()
                            raise IngestionError(f"Expected JSON response. Got text: {text[:100]}", retryable=False, error_code="BAD_CONTENT_TYPE") from exc
                        
                        value = None
                        if json_path:
                            extracted = self._extract_value(data, json_path)
                            if extracted is not None:
                                 try:
                                     value = float(extracted)
                                 except (ValueError, TypeError):
                                     pass
                                     
                        return MetricPayload(
                             metric_id=metric_id,
                             timestamp=datetime.now(timezone.utc),
                             value=value,
                             raw_data=data
                        )
        except aiohttp.ClientError as exc:
            raise IngestionError(f"Network error during ingestion: {exc}", retryable=True) from exc
