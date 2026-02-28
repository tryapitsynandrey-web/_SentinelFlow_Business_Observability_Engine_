# SentinelFlow — Setup Guide

## 1️⃣ Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| pip | Latest |
| make | Any (optional, for Makefile targets) |
| Docker + Compose | Latest (optional, for infra stack) |

## 2️⃣ Clone Project

```bash
git clone <repository_url>
cd SentinelFlow_Business_Observability_Engine
```

## 3️⃣ Virtual Environment

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

Verify:

```bash
which python   # Should point to .venv/bin/python
```

## 4️⃣ Install Dependencies

**Runtime only:**

```bash
pip install .
```

**With dev tools (pytest, mypy, type stubs):**

```bash
pip install ".[dev]"
```

**From requirements.txt (runtime only, pinned):**

```bash
pip install -r requirements.txt
```

## 5️⃣ Environment Variables

Copy the example file:

```bash
cp .env.example .env
```

Edit `.env` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_WEBHOOK_URL` | If using Slack handler | Must be `https://`. Set to empty to skip. |
| `OTLP_ENDPOINT` | No | OpenTelemetry collector address. Default: `http://localhost:4317` |
| `METRICS_PORT` | No | Prometheus metrics server. Default: `9108` |
| `ADMIN_PORT` | No | Health/readiness endpoints. Default: `9109` |
| `DATABASE_URL` | No | SQLite path. Default: `sqlite:///sentinelflow.db` |

**To disable tracing** (when no OTLP collector is running):

In `config.yaml`, set:

```yaml
global:
  observability:
    tracing_enabled: false
```

This prevents the `Connection refused` warnings on port 4317.

## 6️⃣ Configuration

SentinelFlow uses `config.yaml` for pipeline definition.

**Structure:**

```yaml
global:
  concurrency_limit: 10              # Max parallel check executions
  scheduler_mode: "run_once"         # "run_once" or "daemon"
  interval_seconds: 60               # Daemon polling interval (ignored in run_once)
  default_timeout_seconds: 15.0      # Fallback timeout per check

  observability:
    metrics_enabled: true
    tracing_enabled: true            # Set to false if no OTLP collector
    service_name: "sentinelflow"
    otlp_endpoint: "http://localhost:4317"
    metrics_port: 9108
    admin_port: 9109

checks:
  - metric_id: "my_check"           # Unique identifier
    ingestor:
      type: "http_api"
      url: "https://api.example.com/status"
      method: "GET"
    evaluators:
      - type: "threshold"
        operator: "<"                # Supported: >, <, >=, <=
        value: 1
    alert_policy:
      cooldown_seconds: 300
      dedupe_window_seconds: 3600
      severity: "high"              # low | medium | high | critical
    handlers:
      - type: "slack_webhook"
        webhook_url_env_key: "SLACK_WEBHOOK_URL"
    resilience:
      timeout_seconds: 10.0
      max_inflight: 5
      circuit_breaker:
        enabled: true
        failure_threshold: 5
        reset_timeout_seconds: 30
```

**To add a new check:** duplicate an existing `checks` entry and change `metric_id`, `url`, and evaluator settings.

**To disable a handler:** remove it from the `handlers` list or comment it out.

**To adjust resilience:** modify `timeout_seconds`, `failure_threshold`, or set `circuit_breaker.enabled: false`.

## 7️⃣ Running the Application

```bash
python -m src.main
```

With a custom config file:

```bash
python -m src.main --config path/to/config.yaml
```

**Modes:**

| Mode | Behavior |
|------|----------|
| `run_once` | Executes all checks once and exits |
| `daemon` | Runs checks on `interval_seconds` loop until `SIGTERM`/`SIGINT` |

The `concurrency_limit` controls how many checks run in parallel via `asyncio.Semaphore`.

## 8️⃣ Running Tests

```bash
pytest tests/ -v
```

Or via Makefile:

```bash
make test
```

All 42 tests are deterministic — no network calls, no external services required.

## 9️⃣ Static Type Checking

```bash
mypy --strict src observability runtime resilience
```

Or via Makefile:

```bash
make type-check
```

Expected output: `Success: no issues found in N source files`

## 🔟 Docker

**Build the image:**

```bash
docker build -t sentinelflow .
```

**Run with Docker Compose** (includes Prometheus, Grafana, OTLP Collector):

```bash
cd infra
docker compose up --build
```

Ports exposed by default: `9108` (metrics), `9109` (admin).

## 11️⃣ Observability

| Component | Port | Endpoint |
|-----------|------|----------|
| Prometheus | 9108 | `/metrics` (scrape target) |
| Admin | 9109 | `/healthz`, `/readyz` |
| OTLP | 4317 | Trace export (HTTP) |

**If OTLP is not running:** you will see `ConnectionRefusedError` logs on stderr. These are non-fatal — the engine continues operating. To suppress them, set `tracing_enabled: false` in `config.yaml`.

**Metrics exported:**

- `sentinelflow_checks_total` — check executions by status
- `sentinelflow_check_duration_seconds` — latency histogram
- `sentinelflow_inflight_requests` — in-flight gauge
- `sentinelflow_http_requests_total` — outbound HTTP calls

## 12️⃣ Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `CONFIGURATION_INCOMPLETE` on startup | Missing env var for a configured handler | Set `SLACK_WEBHOOK_URL` in `.env` |
| `Connection refused` on port 4317 | No OTLP collector running | Set `tracing_enabled: false` in `config.yaml` |
| `ValidationError` on startup | Invalid `config.yaml` schema | Check field names, types, and required keys against the structure above |
| `Port 9108 already in use` | Another process on the metrics port | Change `METRICS_PORT` in `.env` and `config.yaml` |
| mypy errors on third-party libs | Missing type stubs | Run `pip install ".[dev]"` |
| `ModuleNotFoundError` | Dependencies not installed | Run `pip install .` in activated venv |
| Tests fail with import errors | Running outside project root | Ensure `pythonpath = ["."]` in `pyproject.toml` and run from project root |
