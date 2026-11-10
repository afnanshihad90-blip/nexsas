"""
NEXUS MEDIA AI — Modular Task Queue & Reliability Engine (Step 4)
Designed for seamless Redis & Celery broker integration while providing deterministic
in-memory async queue execution, idempotency deduplication, timeouts, retries,
cancellation, and dead-letter state tracking.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional
import uuid

from app.agents.schemas import AgentTaskInput, AgentTaskOutput, utc_now_iso


@dataclass
class QueuedTaskRecord:
    task_id: str
    idempotency_key: str
    agent_id: str
    stage_name: str
    workflow_run_id: Optional[str]
    status: str  # queued | running | completed | failed | cancelled | dead_letter | not_connected
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 60
    input_payload: Dict[str, Any] = field(default_factory=dict)
    output_envelope: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    dead_letter_reason: Optional[str] = None
    created_at: str = field(default_factory=utc_now_iso)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "idempotency_key": self.idempotency_key,
            "agent_id": self.agent_id,
            "stage_name": self.stage_name,
            "workflow_run_id": self.workflow_run_id,
            "status": self.status,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "input_payload": self.input_payload,
            "output_envelope": self.output_envelope,
            "errors": list(self.errors),
            "dead_letter_reason": self.dead_letter_reason,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "cancelled_at": self.cancelled_at,
        }


class ReliableTaskQueue:
    """
    Modular Task Execution & Reliability Layer suitable for Redis/Celery integration.
    Enforces:
    - Unique task IDs
    - Idempotency deduplication by idempotency_key
    - Configurable retry policies
    - Execution timeout via asyncio.wait_for
    - Dead-letter queue (DLQ) transition when retries are exhausted
    - Task cancellation
    - Complete task execution history
    """

    def __init__(self, broker_backend: str = "in_memory_async_ready_for_redis_celery") -> None:
        self.broker_backend = broker_backend
        self._tasks_by_id: Dict[str, QueuedTaskRecord] = {}
        self._task_id_by_idempotency: Dict[str, str] = {}
        self._cancelled_task_ids: set[str] = set()
        self._running_futures: Dict[str, asyncio.Task[Any]] = {}

    def submit_task(
        self,
        task_input: AgentTaskInput,
    ) -> tuple[QueuedTaskRecord, bool]:
        """
        Registers a task in the queue with idempotency protection.
        Returns (QueuedTaskRecord, duplicate_prevented).
        """
        existing_id = self._task_id_by_idempotency.get(task_input.idempotency_key)
        if existing_id and existing_id in self._tasks_by_id:
            existing_record = self._tasks_by_id[existing_id]
            if existing_record.status != "cancelled":
                return existing_record, True

        task_id = task_input.task_id or f"tsk-{uuid.uuid4().hex[:12]}"
        record = QueuedTaskRecord(
            task_id=task_id,
            idempotency_key=task_input.idempotency_key,
            agent_id=task_input.agent_id,
            stage_name=task_input.stage_name,
            workflow_run_id=task_input.workflow_run_id,
            status="queued",
            retry_count=0,
            max_retries=task_input.max_retries,
            timeout_seconds=task_input.timeout_seconds,
            input_payload=dict(task_input.payload),
        )
        self._tasks_by_id[task_id] = record
        self._task_id_by_idempotency[task_input.idempotency_key] = task_id
        return record, False

    def cancel_task(self, task_id: str, reason: str = "Cancelled by operator") -> QueuedTaskRecord:
        if task_id not in self._tasks_by_id:
            raise KeyError(f"Task '{task_id}' not found.")

        record = self._tasks_by_id[task_id]
        self._cancelled_task_ids.add(task_id)
        if task_id in self._running_futures:
            fut = self._running_futures[task_id]
            if not fut.done():
                fut.cancel()

        record.status = "cancelled"
        record.cancelled_at = utc_now_iso()
        record.completed_at = record.cancelled_at
        if reason not in record.errors:
            record.errors.append(reason)
        return record

    async def execute_with_reliability(
        self,
        task_input: AgentTaskInput,
        executor_fn: Callable[[AgentTaskInput, int], Awaitable[AgentTaskOutput]],
    ) -> tuple[AgentTaskOutput, QueuedTaskRecord, bool]:
        """
        Executes a task with idempotency protection, timeout enforcement,
        automatic retry up to max_retries, cancellation checks, and dead-letter transition.
        """
        record, duplicate_prevented = self.submit_task(task_input)
        if duplicate_prevented and record.output_envelope is not None:
            cached_output = AgentTaskOutput(**record.output_envelope)
            return cached_output, record, True

        if record.task_id in self._cancelled_task_ids or record.status == "cancelled":
            cancelled_out = AgentTaskOutput(
                task_id=record.task_id,
                agent_id=record.agent_id,
                status="cancelled",
                result={},
                errors=record.errors or ["Task was cancelled before execution."],
                started_at=utc_now_iso(),
                completed_at=utc_now_iso(),
                execution_metadata={
                    "attempt": 0,
                    "max_retries": record.max_retries,
                    "idempotency_key": record.idempotency_key,
                },
            )
            record.output_envelope = cancelled_out.to_dict()
            return cancelled_out, record, False

        max_attempts = max(1, record.max_retries + 1)
        last_output: Optional[AgentTaskOutput] = None

        for attempt in range(1, max_attempts + 1):
            if record.task_id in self._cancelled_task_ids:
                record.status = "cancelled"
                record.cancelled_at = utc_now_iso()
                record.completed_at = record.cancelled_at
                cancelled_out = AgentTaskOutput(
                    task_id=record.task_id,
                    agent_id=record.agent_id,
                    status="cancelled",
                    result={},
                    errors=record.errors or ["Task cancelled during execution."],
                    started_at=record.started_at or utc_now_iso(),
                    completed_at=record.completed_at,
                    execution_metadata={
                        "attempt": attempt,
                        "max_retries": record.max_retries,
                        "idempotency_key": record.idempotency_key,
                    },
                )
                record.output_envelope = cancelled_out.to_dict()
                return cancelled_out, record, False

            record.status = "running"
            record.started_at = record.started_at or utc_now_iso()
            if attempt > 1:
                record.retry_count = attempt - 1

            try:
                output = await asyncio.wait_for(
                    executor_fn(task_input, attempt),
                    timeout=float(record.timeout_seconds),
                )
                last_output = output
            except asyncio.TimeoutError:
                now_str = utc_now_iso()
                last_output = AgentTaskOutput(
                    task_id=record.task_id,
                    agent_id=record.agent_id,
                    status="failed",
                    result={},
                    errors=[
                        f"Execution timed out after {record.timeout_seconds}s on attempt {attempt}."
                    ],
                    started_at=record.started_at,
                    completed_at=now_str,
                    execution_metadata={
                        "attempt": attempt,
                        "max_retries": record.max_retries,
                        "timeout_seconds": record.timeout_seconds,
                        "idempotency_key": record.idempotency_key,
                        "timed_out": True,
                    },
                )
            except asyncio.CancelledError:
                record.status = "cancelled"
                record.cancelled_at = utc_now_iso()
                record.completed_at = record.cancelled_at
                cancelled_out = AgentTaskOutput(
                    task_id=record.task_id,
                    agent_id=record.agent_id,
                    status="cancelled",
                    result={},
                    errors=["Task execution cancelled."],
                    started_at=record.started_at or utc_now_iso(),
                    completed_at=record.completed_at,
                    execution_metadata={
                        "attempt": attempt,
                        "max_retries": record.max_retries,
                        "idempotency_key": record.idempotency_key,
                    },
                )
                record.output_envelope = cancelled_out.to_dict()
                return cancelled_out, record, False

            if last_output.status in ("completed", "not_connected"):
                record.status = last_output.status
                record.completed_at = last_output.completed_at
                record.errors = list(last_output.errors)
                record.output_envelope = last_output.to_dict()
                return last_output, record, False

            record.errors = list(last_output.errors)

            # Do not retry permanent policy or disabled/paused state errors
            non_retryable = any(
                phrase in err.lower()
                for err in last_output.errors
                for phrase in ("is disabled", "is paused", "security policy violation")
            )
            if non_retryable:
                record.status = "failed"
                record.completed_at = last_output.completed_at
                record.output_envelope = last_output.to_dict()
                return last_output, record, False

        # Retries exhausted -> transition to dead_letter state
        assert last_output is not None
        record.status = "dead_letter"
        record.completed_at = utc_now_iso()
        record.dead_letter_reason = (
            f"Exhausted max_retries ({record.max_retries}) after {max_attempts} attempts. "
            f"Last error: {'; '.join(record.errors)}"
        )
        dlq_metadata = dict(last_output.execution_metadata)
        dlq_metadata["dead_letter"] = True
        dlq_metadata["dead_letter_reason"] = record.dead_letter_reason
        dlq_metadata["attempts_executed"] = max_attempts

        dlq_output = AgentTaskOutput(
            task_id=record.task_id,
            agent_id=record.agent_id,
            status="dead_letter",
            result=last_output.result,
            errors=record.errors + [record.dead_letter_reason],
            started_at=last_output.started_at,
            completed_at=record.completed_at,
            execution_metadata=dlq_metadata,
        )
        record.output_envelope = dlq_output.to_dict()
        return dlq_output, record, False

    def enqueue_background(
        self,
        task_input: AgentTaskInput,
        executor_fn: Callable[[AgentTaskInput, int], Awaitable[AgentTaskOutput]],
    ) -> tuple[QueuedTaskRecord, bool]:
        """
        Enqueues a task for asynchronous background execution so HTTP request handlers
        return immediately with the queued task_id instead of blocking on long research jobs.
        """
        record, duplicate_prevented = self.submit_task(task_input)
        if duplicate_prevented:
            return record, True

        async def _runner() -> None:
            try:
                await self.execute_with_reliability(task_input, executor_fn)
            finally:
                self._running_futures.pop(record.task_id, None)

        loop = asyncio.get_running_loop()
        self._running_futures[record.task_id] = loop.create_task(_runner())
        return record, False

    def get_task(self, task_id: str) -> Optional[QueuedTaskRecord]:
        return self._tasks_by_id.get(task_id)

    def list_tasks(self, agent_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        records = list(self._tasks_by_id.values())
        if agent_id:
            records = [r for r in records if r.agent_id == agent_id]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return [r.to_dict() for r in records[:limit]]

    def get_queue_stats(self) -> Dict[str, Any]:
        counts = {
            "queued": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "dead_letter": 0,
            "not_connected": 0,
        }
        for rec in self._tasks_by_id.values():
            counts[rec.status] = counts.get(rec.status, 0) + 1
        return {
            "broker_backend": self.broker_backend,
            "redis_celery_ready": True,
            "total_tasks": len(self._tasks_by_id),
            "counts_by_status": counts,
        }
