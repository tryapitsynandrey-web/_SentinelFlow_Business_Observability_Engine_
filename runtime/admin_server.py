import asyncio
from typing import Awaitable, Callable
from aiohttp import web
from runtime.readiness import Readiness
import prometheus_client

AdminAppFactory = Callable[[], Awaitable[web.Application]]

async def healthz(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"}, status=200)

async def readyz(request: web.Request) -> web.Response:
    readiness: Readiness = request.app["readiness"]
    state = readiness.snapshot()
    
    if state["ready"]:
        return web.json_response(state, status=200)
    return web.json_response(state, status=503)

async def metrics(request: web.Request) -> web.Response:
    data = prometheus_client.generate_latest()
    # prometheus_client returns content_type with charset, e.g. "text/plain; version=0.0.4; charset=utf-8"
    # aiohttp does not allow charset in content_type argument, so we set it via headers.
    return web.Response(body=data, headers={"Content-Type": prometheus_client.CONTENT_TYPE_LATEST})

async def start_admin_server(port: int, readiness: Readiness) -> web.AppRunner:
    app = web.Application()
    app["readiness"] = readiness
    
    app.router.add_get("/healthz", healthz)
    app.router.add_get("/readyz", readyz)
    app.router.add_get("/metrics", metrics)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    return runner
