import asyncio
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from src.engine.registry import Registry
from src.models.entities import MetricPayload, AlertEvent
from src.core.policies import AlertPolicy
from src.utils.logger import get_logger
from src.config.parser import AppConfig
from src.utils.exceptions import IngestionError
from src.core.history import ExecutionHistory
from observability.metrics import Metrics
from observability.context import span
from runtime.resilience import ResilienceManager

logger = get_logger(__name__)


class Executor:
    """
    Production-grade bounded concurrent executor with OpenTelemetry spans
    and Circuit Break integrations.
    """

    def __init__(
        self,
        concurrency_limit: int,
        policy: AlertPolicy,
        metrics: Metrics,
        resilience: ResilienceManager
    ) -> None:
        self._semaphore = asyncio.Semaphore(concurrency_limit)
        self._policy = policy
        self.history = ExecutionHistory(max_size=100)
        self.metrics = metrics
        self.resilience = resilience

    async def startup(self, config: AppConfig) -> None:
        cfg_dict = config.model_dump(by_alias=True)
        checks: Any = cfg_dict.get("checks", [])
        if not isinstance(checks, list):
            checks = []
            
        for chk in checks:
            if not isinstance(chk, dict):
                continue
            
            ing_cfg = chk.get("ingestor")
            if isinstance(ing_cfg, dict):
                i_type = ing_cfg.get("type")
                if isinstance(i_type, str):
                    try:
                        ingestor = Registry.get_ingestor(i_type)
                        if hasattr(ingestor, "startup"):
                            await ingestor.startup()
                    except Exception as e:
                        logger.error(f"Failed to startup ingestor {i_type}", extra={"error": str(e)})

            handlers_cfg = chk.get("handlers", [])
            if isinstance(handlers_cfg, list):
                for h_cfg in handlers_cfg:
                    if isinstance(h_cfg, dict):
                        h_type = h_cfg.get("type")
                        if isinstance(h_type, str):
                            try:
                                handler = Registry.get_handler(h_type)
                                if hasattr(handler, "startup"):
                                    await handler.startup()
                            except Exception as e:
                                logger.error(f"Failed to startup handler {h_type}", extra={"error": str(e)})

    async def shutdown(self, config: AppConfig) -> None:
        cfg_dict = config.model_dump(by_alias=True)
        checks: Any = cfg_dict.get("checks", [])
        if not isinstance(checks, list):
            checks = []
            
        for chk in checks:
            if not isinstance(chk, dict):
                continue
            
            ing_cfg = chk.get("ingestor")
            if isinstance(ing_cfg, dict):
                i_type = ing_cfg.get("type")
                if isinstance(i_type, str):
                    try:
                        ingestor = Registry.get_ingestor(i_type)
                        if hasattr(ingestor, "shutdown"):
                            await ingestor.shutdown()
                    except Exception as e:
                        logger.error(f"Failed to shutdown ingestor {i_type}", extra={"error": str(e)})

            handlers_cfg = chk.get("handlers", [])
            if isinstance(handlers_cfg, list):
                for h_cfg in handlers_cfg:
                    if isinstance(h_cfg, dict):
                        h_type = h_cfg.get("type")
                        if isinstance(h_type, str):
                            try:
                                handler = Registry.get_handler(h_type)
                                if hasattr(handler, "shutdown"):
                                    await handler.shutdown()
                            except Exception as e:
                                logger.error(f"Failed to shutdown handler {h_type}", extra={"error": str(e)})

    async def _execute_single_check(
        self,
        check_config: Dict[str, Any],
        scheduler_mode: str
    ) -> None:
        metric_id = check_config.get("metric_id")
        if not isinstance(metric_id, str) or not metric_id:
            metric_id = "unknown"
            
        resilience_cfg = check_config.get("resilience", {})
        if not isinstance(resilience_cfg, dict):
            resilience_cfg = {}
            
        check_resilience = await self.resilience.for_check(metric_id, resilience_cfg)
        
        async def run_pipeline() -> None:
            self.metrics.inc_check(metric_id, "started")
            self.metrics.inflight_inc(metric_id)
            context_logger = get_logger(f"{__name__}.{metric_id}")
            start_time = time.perf_counter()
            
            async with span(
                "check.execute",
                check_id=metric_id,
                scheduler_mode=scheduler_mode
            ):
                try:
                    # INGESTION
                    ingestor_cfg = check_config.get("ingestor")
                    if not isinstance(ingestor_cfg, dict):
                        raise ValueError("Missing or invalid 'ingestor' config")
                        
                    ingestor_type = ingestor_cfg.get("type")
                    if not isinstance(ingestor_type, str):
                        raise ValueError("Ingestor 'type' must be a string")
                        
                    ingestor = Registry.get_ingestor(ingestor_type)
                    
                    ingest_start = time.perf_counter()
                    async with span("check.ingest", check_id=metric_id):
                        payload: MetricPayload = await ingestor.fetch(metric_id, ingestor_cfg)
                    self.metrics.observe_ingest(metric_id, time.perf_counter() - ingest_start)
                    
                    # EVALUATION
                    valid_events: List[AlertEvent] = []
                    evaluators_cfg = check_config.get("evaluators")
                    if not isinstance(evaluators_cfg, list):
                        evaluators_cfg = []
        
                    async with span("check.evaluate", check_id=metric_id):
                        for eval_cfg in evaluators_cfg:
                            if not isinstance(eval_cfg, dict):
                                continue
                            eval_type = eval_cfg.get("type")
                            if not isinstance(eval_type, str):
                                continue
                                
                            evaluator = Registry.get_evaluator(eval_type)
                            event = evaluator.evaluate(payload, eval_cfg)
                            if event:
                                valid_events.append(event)
        
                    if not valid_events:
                        duration = time.perf_counter() - start_time
                        context_logger.info("Check passed.", extra={"check_id": metric_id, "duration_ms": duration * 1000})
                        await self.history.add_result(metric_id, True, duration * 1000)
                        self.metrics.observe_check_duration(metric_id, duration)
                        self.metrics.inc_check(metric_id, "passed")
                        self.metrics.record_success(metric_id, datetime.now(timezone.utc).timestamp())
                        return
        
                    # POLICY + DISPATCH
                    policy_cfg = check_config.get("alert_policy", {})
                    if not isinstance(policy_cfg, dict):
                        policy_cfg = {}
                        
                    cooldown_raw = policy_cfg.get("cooldown_seconds", 300)
                    cooldown = int(cooldown_raw) if isinstance(cooldown_raw, (int, float, str)) and str(cooldown_raw).isdigit() else 300
                    
                    dedupe_raw = policy_cfg.get("dedupe_window_seconds", 3600)
                    dedupe = int(dedupe_raw) if isinstance(dedupe_raw, (int, float, str)) and str(dedupe_raw).isdigit() else 3600
        
                    handlers_cfg = check_config.get("handlers", [])
                    if not isinstance(handlers_cfg, list):
                        handlers_cfg = []
        
                    for alert_event in valid_events:
                        if not self._policy.should_dispatch(
                            alert_event.metric_id,
                            alert_event.evaluator_type,
                            alert_event.severity,
                            cooldown,
                            dedupe,
                            event=alert_event,
                        ):
                            context_logger.info("Alert suppressed by policy.", extra={"check_id": metric_id})
                            self.metrics.inc_alert(metric_id, alert_event.evaluator_type, alert_event.severity, "suppressed")
                            continue
        
                        dispatch_tasks = []
                        for handler_cfg in handlers_cfg:
                            if not isinstance(handler_cfg, dict):
                                continue
                            handler_type = handler_cfg.get("type")
                            if not isinstance(handler_type, str):
                                continue
                            
                            async def run_dispatch(h: Any, evt: AlertEvent, cfg: Dict[str, Any], h_type: str) -> None:
                                d_start = time.perf_counter()
                                async with span("check.dispatch", check_id=metric_id, handler=h_type):
                                    await h.dispatch(evt, cfg)
                                self.metrics.observe_dispatch(metric_id, h_type, time.perf_counter() - d_start)
                                self.metrics.inc_alert(metric_id, evt.evaluator_type, evt.severity, "dispatched")
                                
                            handler = Registry.get_handler(handler_type)
                            dispatch_tasks.append(
                                run_dispatch(handler, alert_event, handler_cfg, handler_type)
                            )
        
                        results = await asyncio.gather(*dispatch_tasks, return_exceptions=True)
                        for res in results:
                            if isinstance(res, Exception):
                                err_code = getattr(res, "error_code", "UNKNOWN_ERROR")
                                context_logger.error(
                                    "Handler dispatch failed.",
                                    extra={"check_id": metric_id, "error": str(res), "error_code": err_code, "duration_ms": (time.perf_counter() - start_time) * 1000},
                                )
        
                    duration = time.perf_counter() - start_time
                    context_logger.info("Check completed with alerts.", extra={"check_id": metric_id, "duration_ms": duration * 1000})
                    await self.history.add_result(metric_id, True, duration * 1000)
                    self.metrics.observe_check_duration(metric_id, duration)
                    self.metrics.inc_check(metric_id, "alerted")
                    self.metrics.record_success(metric_id, datetime.now(timezone.utc).timestamp())
        
                except asyncio.CancelledError:
                    context_logger.warning("Check cancelled.", extra={"check_id": metric_id})
                    self.metrics.inc_check(metric_id, "cancelled")
                    raise
        
                except Exception as e:
                    duration = time.perf_counter() - start_time
                    
                    if "CircuitBreakerOpenException" in str(type(e)) or "Circuit is OPEN" in str(e):
                        context_logger.error(
                            "Execution skipped.",
                            extra={"check_id": metric_id, "duration_ms": duration * 1000, "error_code": "CIRCUIT_OPEN", "status": "skipped"}
                        )
                        self.metrics.inc_check(metric_id, "skipped")
                        await self.history.add_result(metric_id, False, duration * 1000)
                        return
                    
                    err_code = getattr(e, "error_code", "EXECUTION_ERROR")
                    context_logger.error(
                        "Execution failed.",
                        extra={"check_id": metric_id, "duration_ms": duration * 1000, "error_code": err_code, "error": str(e)},
                    )
                    await self.history.add_result(metric_id, False, duration * 1000)
                    self.metrics.observe_check_duration(metric_id, duration)
                    self.metrics.inc_check(metric_id, "failed")
                    raise
                finally:
                    self.metrics.inflight_dec(metric_id)

        try:
            start_outer = time.perf_counter()
            await asyncio.wait_for(
                check_resilience.execute(run_pipeline),
                timeout=check_resilience.timeout_seconds
            )
        except asyncio.TimeoutError as exc:
            duration_outer = time.perf_counter() - start_outer
            get_logger(f"{__name__}.{metric_id}").error(
                "Check timed out.",
                extra={"check_id": metric_id, "duration_ms": duration_outer * 1000, "error_code": "TIMEOUT"}
            )
            await self.history.add_result(metric_id, False, duration_outer * 1000)
            self.metrics.inc_check(metric_id, "timeout")
            self.metrics.observe_check_duration(metric_id, duration_outer)

    async def execute_batch(self, config: AppConfig) -> None:

        cfg_dict = config.model_dump(by_alias=True)
        checks: Any = cfg_dict.get("checks", [])
        if not isinstance(checks, list):
            checks = []
            
        global_cfg: Any = cfg_dict.get("global", {})
        if not isinstance(global_cfg, dict):
            global_cfg = {}
        
        scheduler_mode = str(global_cfg.get("scheduler_mode", "run_once"))

        async def _bounded_execute(check_cfg: Dict[str, Any]) -> None:
            async with self._semaphore:
                await self._execute_single_check(check_cfg, scheduler_mode)

        tasks = [_bounded_execute(chk) for chk in checks]

        start_batch = time.perf_counter()
        logger.info(f"Starting batch execution of {len(tasks)} checks...")

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error("A check in the batch failed critically.", exc_info=res)

        except asyncio.CancelledError:
            logger.warning("Batch execution cancelled.")
            raise

        duration = (time.perf_counter() - start_batch) * 1000
        logger.info(
            "Batch execution completed.",
            extra={"duration_ms": duration, "tasks": len(tasks)},
        )