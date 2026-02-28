# 🛰️ SentinelFlow — Business Observability Engine

**SentinelFlow** is an asynchronous, config-driven observability engine that evaluates business metrics, detects threshold breaches, and dispatches structured alerts — with built-in resilience, tracing, and Prometheus telemetry.

Built for **SRE teams**, **platform engineers**, and **backend developers** who need reliable metric monitoring without vendor lock-in.

---

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Typing](https://img.shields.io/badge/mypy-strict-blue?logo=python&logoColor=white)
![Async](https://img.shields.io/badge/async-asyncio-green?logo=python&logoColor=white)
![Prometheus](https://img.shields.io/badge/Metrics-Prometheus-E6522C?logo=prometheus&logoColor=white)
![OpenTelemetry](https://img.shields.io/badge/Tracing-OpenTelemetry-7B61FF?logo=opentelemetry&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-42%20Passing-brightgreen)

---

## 📌 Business Context

Modern infrastructure generates metrics across dozens of services. Teams face two recurring problems:

1. **Alert fatigue** — noisy, undeduplicated notifications from naive threshold checks.
2. **Fragile monitoring** — one failing check stalls the entire pipeline.

SentinelFlow addresses both by providing:

- **Isolated, bounded-concurrency execution** — one slow or failing check never blocks others.
- **Cooldown-based alert aggregation** — duplicate alerts are suppressed within configurable windows.
- **Circuit breakers per check** — cascading failures are automatically contained.
- **Full pipeline observability** — every ingestion, evaluation, and dispatch is traced and metered.

**Who benefits:** SRE teams reducing MTTR, backend teams adding custom business metric checks, platform engineers building internal monitoring foundations.

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.11+ |
| Async Runtime | `asyncio`, `aiohttp` |
| Config & Validation | Pydantic v2 (strict models), PyYAML |
| Metrics | `prometheus-client` (Counter, Histogram, Gauge) |
| Tracing | OpenTelemetry SDK + OTLP HTTP exporter |
| Resilience | Circuit breaker, per-check timeouts, bounded semaphores |
| Retry | `tenacity` with exponential backoff + jitter |
| Persistence | `aiosqlite` (async SQLite) |
| Testing | `pytest`, `pytest-asyncio` (42 deterministic tests) |
| Type Safety | `mypy --strict` (zero errors, zero `type: ignore`) |
| Containerization | Docker, Docker Compose |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        config.yaml + .env                        │
└──────────────┬───────────────────────────────────┬───────────────┘
               │                                   │
        ┌──────▼──────┐                     ┌──────▼──────┐
        │  AppConfig  │                     │ AppSettings │
        │ (Pydantic)  │                     │(env secrets)│
        └──────┬──────┘                     └─────────────┘
               │
        ┌──────▼──────┐
        │  Scheduler  │──── run_once / daemon
        └──────┬──────┘
               │
        ┌──────▼──────┐     ┌──────────────┐
        │  Executor   │────▶│  Resilience   │
        │ (semaphore) │     │  (CB + timeout)│
        └──┬───┬───┬──┘     └──────────────┘
           │   │   │
     ┌─────▼┐ ┌▼────┐ ┌─▼───────┐
     │Ingest│ │Eval  │ │Handler  │
     │(HTTP)│ │(Thr/ │ │(Slack)  │
     │      │ │Fresh)│ │         │
     └──────┘ └──────┘ └─────────┘
           │       │         │
     ┌─────▼───────▼─────────▼─────┐
     │     Observability Layer      │
     │  Prometheus │ OTLP Tracing   │
     └─────────────────────────────┘
```

| Component | Responsibility |
|-----------|---------------|
| **Ingestor** | Fetches metric payloads from external sources (HTTP REST APIs) |
| **Evaluator** | Analyzes payloads against configurable rules (threshold, freshness) |
| **AlertPolicy** | Deduplicates and rate-limits alerts using cooldown windows |
| **Executor** | Orchestrates check execution with bounded concurrency |
| **Resilience** | Per-check circuit breakers, timeouts, and semaphore isolation |
| **Observability** | Prometheus counters/histograms + OpenTelemetry distributed traces |

---

## ⚡ Key Capabilities

| Capability | Detail |
|------------|--------|
| 🔒 **Circuit Breaker** | Prevents cascading failures — auto-opens after N failures, resets after timeout |
| ⏱️ **Per-Check Timeout** | Each check runs in isolated `asyncio.wait_for` — no blocking the pipeline |
| 📊 **Prometheus Metrics** | Check counts, durations, in-flight gauges, HTTP request tracking |
| 🔍 **Distributed Tracing** | End-to-end spans for ingest → evaluate → dispatch via OTLP |
| 🔇 **Alert Deduplication** | Cooldown + dedupe windows suppress repeated alerts intelligently |
| 🩺 **Health Endpoints** | `/healthz` and `/readyz` for liveness/readiness probes |
| 📝 **Structured Logging** | JSON-formatted logs with correlation context for production debugging |
| 🔄 **Retry with Backoff** | Exponential backoff + jitter on transient network failures |
| 🧪 **Strict Type Safety** | `mypy --strict` across entire codebase — zero `Any` leakage |

---

## 📈 Observability Dashboard

SentinelFlow exposes three observability surfaces:

| Endpoint | Port | Purpose |
|----------|------|---------|
| Prometheus `/metrics` | `9108` | Scrape target for Grafana/Alertmanager |
| Admin `/healthz` `/readyz` | `9109` | Kubernetes-style liveness/readiness probes |
| OTLP traces | `4317` | Distributed tracing to Jaeger/Tempo/Collector |

**Metrics exported:**

- `sentinelflow_checks_total` — total checks executed (by check_id, status)
- `sentinelflow_check_duration_seconds` — histogram of check latencies
- `sentinelflow_inflight_requests` — gauge of currently running checks
- `sentinelflow_http_requests_total` — outbound HTTP request counts

---

## 🚀 How to Run

### Local Setup

```bash
# 1. Clone
git clone <repository_url>
cd SentinelFlow_Business_Observability_Engine

# 2. Create virtualenv
python3 -m venv .venv
source .venv/bin/activate        # Mac/Linux
# .venv\Scripts\activate          # Windows

# 3. Install
pip install .                     # Runtime only
pip install ".[dev]"              # With pytest + mypy

# 4. Configure
cp .env.example .env
# Edit .env → set SLACK_WEBHOOK_URL if using Slack handler

# 5. Run
python -m src.main
```

### Docker Setup

```bash
cd infra
docker compose up --build
```

### Run Tests

```bash
pytest tests/ -v                  # 42 deterministic tests
```

### Run Type Checks

```bash
mypy --strict src observability runtime resilience
```

---

## ⚙️ Configuration Guide

SentinelFlow uses two configuration sources:

### `config.yaml` — Pipeline Definition

```yaml
global:
  concurrency_limit: 10           # Max parallel checks
  scheduler_mode: "run_once"      # or "daemon"
  interval_seconds: 60            # Daemon polling interval
  default_timeout_seconds: 15.0

checks:
  - metric_id: "api_health"
    ingestor:
      type: "http_api"
      url: "https://api.example.com/status"
      method: "GET"
    evaluators:
      - type: "threshold"
        operator: "<"
        value: 1
    handlers:
      - type: "slack_webhook"
        webhook_url_env_key: "SLACK_WEBHOOK_URL"
    resilience:
      timeout_seconds: 10.0
      circuit_breaker:
        enabled: true
        failure_threshold: 5
```

### `.env` — Secrets & Environment

| Variable | Purpose |
|----------|---------|
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook endpoint (must be HTTPS) |
| `OTLP_ENDPOINT` | OpenTelemetry collector address |
| `METRICS_PORT` | Prometheus metrics server port (default: 9108) |
| `ADMIN_PORT` | Admin health/ready server port (default: 9109) |
| `DATABASE_URL` | SQLite connection string |

---

## 💡 Business Impact

Even as an independent engine, SentinelFlow demonstrates production patterns that directly translate to organizational value:

- **Proactive failure detection** — catches metric degradation before users report incidents
- **Reduced alert fatigue** — deduplication and cooldown windows cut noise by suppressing repeat notifications
- **Cascading failure prevention** — circuit breakers isolate unhealthy checks automatically
- **Full pipeline visibility** — Prometheus metrics + OTLP traces enable data-driven SRE decisions
- **Lightweight deployment** — single binary, no infrastructure dependencies beyond Python

Suitable as a foundation for internal monitoring platforms, on-call alerting, and SLA compliance tracking.

---

## 🏁 Project Maturity

| Dimension | Status |
|-----------|--------|
| Type Safety | `mypy --strict` — zero errors, zero `type: ignore` |
| Test Suite | 42 deterministic tests (unit + integration) |
| Dependency Health | `pip check` clean, no broken requirements |
| Docker | Production Dockerfile + Compose stack |
| CI Ready | `make test && make type-check` single-command validation |
| Architecture | Clean Architecture with strict layer boundaries |
