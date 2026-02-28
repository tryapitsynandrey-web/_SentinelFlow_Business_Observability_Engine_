import asyncio
import sys
import argparse
import signal
from typing import NoReturn, Any

from src.utils.logger import configure_logging, get_logger
from src.utils.exceptions import ConfigError
from src.config.parser import load_config, AppConfig
from src.core.policies import AlertPolicy
from src.engine.executor import Executor
from src.engine.scheduler import Scheduler


logger = get_logger("sentinelflow")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SentinelFlow Observability Engine"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to YAML configuration file",
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()

    try:
        logger.info("Loading configuration...", extra={"config_path": args.config})
        config: AppConfig = load_config(args.config)
    except ConfigError as e:
        logger.error(str(e))
        return 1

    from src.config.settings import get_settings
    settings = get_settings()

    cfg_dict = config.model_dump(by_alias=True)
    checks: list[dict[str, Any]] = cfg_dict.get("checks", []) if isinstance(cfg_dict.get("checks"), list) else []
    configured_handlers: set[str] = set()
    for chk in checks:
        if not isinstance(chk, dict):
            continue
        handlers_cfg = chk.get("handlers", [])
        if isinstance(handlers_cfg, list):
            for h in handlers_cfg:
                if isinstance(h, dict):
                    h_type = h.get("type")
                    if isinstance(h_type, str):
                        configured_handlers.add(h_type)

    missing_vars = settings.validate_required_integrations(list(configured_handlers))

    # Example Check for DB if a persistence module ever activates
    if "persistence" in configured_handlers and not settings.database_url:
        missing_vars.append("DATABASE_URL")

    if missing_vars:
        logger.error(
            "Configuration incomplete.",
            extra={
                "error_code": "CONFIGURATION_INCOMPLETE",
                "missing": missing_vars
            }
        )
        return 1

    from observability.tracing import configure_tracing
    from observability.metrics import Metrics, start_metrics_server
    from runtime.readiness import Readiness
    from runtime.admin_server import start_admin_server
    from runtime.resilience import ResilienceManager

    # Strict typed access
    global_cfg = config.global_config
    concurrency_limit: int = global_cfg.concurrency_limit
    scheduler_mode: str = global_cfg.scheduler_mode
    obs_cfg = global_cfg.observability

    if obs_cfg.tracing_enabled:
        configure_tracing(obs_cfg.service_name, obs_cfg.otlp_endpoint)

    metrics_client = Metrics()
    if obs_cfg.metrics_enabled:
        start_metrics_server(obs_cfg.metrics_port)

    readiness = Readiness()
    admin_runner = None

    try:
        admin_runner = await start_admin_server(obs_cfg.admin_port, readiness)
    except Exception as e:
        logger.error(f"Failed to start admin server: {e}")

    policy = AlertPolicy()
    resilience_manager = ResilienceManager()
    executor = Executor(
        concurrency_limit=concurrency_limit,
        policy=policy,
        metrics=metrics_client,
        resilience=resilience_manager
    )
    scheduler = Scheduler(executor=executor)

    shutdown_event = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("Shutdown signal received.")
        shutdown_event.set()

    loop = asyncio.get_running_loop()

    # Register graceful shutdown signals (Unix only)
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            # Windows fallback
            pass

    try:
        await executor.startup(config)
        readiness.set_ready()

        if scheduler_mode == "run_once":
            await scheduler.run_once(config)

        elif scheduler_mode == "daemon":
            daemon_task = asyncio.create_task(
                scheduler.run_daemon(config)
            )

            await shutdown_event.wait()

            logger.info("Cancelling daemon scheduler...")
            daemon_task.cancel()
            readiness.set_not_ready("Shutting down")

            try:
                await daemon_task
            except asyncio.CancelledError:
                logger.info("Daemon task cancelled successfully.")

        else:
            logger.error(
                "Invalid scheduler_mode detected.",
                extra={"scheduler_mode": scheduler_mode},
            )
            return 1

    except asyncio.CancelledError:
        logger.info("Application cancelled.")
    except Exception:
        logger.exception("Fatal application error.")
        return 1
    finally:
        try:
            await executor.shutdown(config)
            if admin_runner:
                await admin_runner.cleanup()
        except Exception:
            logger.exception("Error executing graceful shutdown routines.")

    logger.info("Application shutdown complete.")
    return 0


def main() -> NoReturn:
    configure_logging()

    try:
        exit_code = asyncio.run(async_main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received.")
        sys.exit(0)


if __name__ == "__main__":
    main()