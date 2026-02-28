import asyncio
import time
from typing import Any, Dict

from src.engine.executor import Executor
from src.utils.logger import get_logger
from src.config.parser import AppConfig

logger = get_logger(__name__)


class Scheduler:
    """
    Production-grade scheduler supporting:
    - run-once mode
    - daemon mode with fixed-interval scheduling
    - graceful shutdown
    - drift control
    """

    def __init__(self, executor: Executor):
        self._executor = executor
        self._running = False

    async def run_once(self, config: AppConfig) -> None:
        logger.info("Scheduler running in ONE-SHOT mode.")
        await self._executor.execute_batch(config)

    async def run_daemon(self, config: AppConfig) -> None:

        interval: int = config.global_config.interval_seconds

        logger.info(
            f"Scheduler running in DAEMON mode (interval={interval}s)."
        )

        self._running = True
        next_run = time.perf_counter()

        try:
            while self._running:

                next_run += interval
                cycle_start = time.perf_counter()

                await self._executor.execute_batch(config)

                # Maintenance hook (better encapsulation)
                if hasattr(self._executor, "maintenance"):
                    await self._executor.maintenance()

                now = time.perf_counter()
                sleep_time = next_run - now

                if sleep_time > 0:
                    logger.info(
                        f"Sleeping {sleep_time:.2f}s until next cycle."
                    )
                    await asyncio.sleep(sleep_time)
                else:
                    logger.warning(
                        f"Execution overran interval by {-sleep_time:.2f}s."
                    )

        except asyncio.CancelledError:
            logger.info("Scheduler received cancellation. Shutting down...")
            self._running = False
            raise

        finally:
            logger.info("Scheduler stopped.")