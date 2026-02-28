from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Metrics definitions
_checks_total = Counter(
    "sentinelflow_checks_total",
    "Total checks executed",
    ["check_id", "status"]
)

_alerts_total = Counter(
    "sentinelflow_alerts_total",
    "Total alerts processed",
    ["check_id", "evaluator", "severity", "action"]
)

_http_requests_total = Counter(
    "sentinelflow_http_requests_total",
    "Total HTTP requests made by ingestor",
    ["check_id", "host", "method", "status_class"]
)

_check_duration = Histogram(
    "sentinelflow_check_duration_seconds",
    "Duration of check execution",
    ["check_id"]
)

_ingest_duration = Histogram(
    "sentinelflow_ingest_duration_seconds",
    "Duration of data ingestion",
    ["check_id"]
)

_dispatch_duration = Histogram(
    "sentinelflow_dispatch_duration_seconds",
    "Duration of alert dispatch",
    ["check_id", "handler"]
)

_inflight_requests = Gauge(
    "sentinelflow_inflight_requests",
    "Number of requests currently inflight",
    ["check_id"]
)

_last_success = Gauge(
    "sentinelflow_last_success_timestamp",
    "Timestamp of last successful check",
    ["check_id"]
)

class Metrics:
    def inc_check(self, check_id: str, status: str) -> None:
        _checks_total.labels(check_id=check_id, status=status).inc()

    def observe_check_duration(self, check_id: str, seconds: float) -> None:
        _check_duration.labels(check_id=check_id).observe(seconds)

    def inflight_inc(self, check_id: str) -> None:
        _inflight_requests.labels(check_id=check_id).inc()

    def inflight_dec(self, check_id: str) -> None:
        _inflight_requests.labels(check_id=check_id).dec()

    def inc_alert(self, check_id: str, evaluator: str, severity: str, action: str) -> None:
        _alerts_total.labels(
            check_id=check_id,
            evaluator=evaluator,
            severity=severity,
            action=action
        ).inc()

    def inc_http_request(self, check_id: str, host: str, method: str, status_class: str) -> None:
        try:
            _http_requests_total.labels(
                check_id=check_id,
                host=host,
                method=method,
                status_class=status_class
            ).inc()
        except Exception:
            pass

    def observe_ingest(self, check_id: str, seconds: float) -> None:
        _ingest_duration.labels(check_id=check_id).observe(seconds)

    def observe_dispatch(self, check_id: str, handler: str, seconds: float) -> None:
        _dispatch_duration.labels(check_id=check_id, handler=handler).observe(seconds)
        
    def record_success(self, check_id: str, timestamp: float) -> None:
        _last_success.labels(check_id=check_id).set(timestamp)

def start_metrics_server(port: int) -> None:
    start_http_server(port)
