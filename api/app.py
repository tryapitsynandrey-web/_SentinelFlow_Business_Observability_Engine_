from fastapi import FastAPI, Response
from typing import Any
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from src.config.parser import load_config
from src.core.policies import AlertPolicy

app = FastAPI(title="SentinelFlow Hybrid API")

# For demonstration of isolated in-memory state
global_policy = AlertPolicy()

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/metrics")
async def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.get("/checks")
async def checks() -> dict[str, list[dict[str, str]]]:
    # Loading configuration independently safely
    config = load_config("config.yaml")
    active_checks = [
        {"metric_id": check.metric_id, "ingestor_type": check.ingestor.type}
        for check in config.checks
    ]
    return {"active_checks": active_checks}

@app.get("/policy-state")
async def policy_state() -> dict[str, dict[str, Any]]:
    # Exposing the isolated in-memory state structure
    return {
        "last_seen": global_policy._last_seen,
        "last_dispatched": global_policy._last_dispatched
    }
