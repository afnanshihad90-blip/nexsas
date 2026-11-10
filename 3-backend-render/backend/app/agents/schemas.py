"""
NEXUS MEDIA AI — Typed Agent Communication & Configuration Schemas (Step 4)
Enforces structured JSON input/output envelopes across the Orchestrator and all 9 Specialist Agents.
Prevents arbitrary executable code injection between agents.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field, field_validator
except ImportError:  # Fallback for standard-library unittest environments

    class BaseModel:  # type: ignore[no-redef]
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

        def model_dump(self) -> Dict[str, Any]:
            return dict(self.__dict__)

    def Field(default: Any = None, **kwargs: Any) -> Any:  # type: ignore[misc]
        if default is ... and "default_factory" in kwargs:
            return kwargs["default_factory"]()
        return default

    def field_validator(*_args: Any, **_kwargs: Any):  # type: ignore[misc]
        def decorator(fn: Any) -> Any:
            return fn

        return decorator


FORBIDDEN_CODE_PATTERNS = (
    "__import__",
    "__subclasses__",
    "__builtins__",
    "__globals__",
    "eval(",
    "exec(",
    "compile(",
    "os.system(",
    "subprocess.",
    "pickle.loads",
)


def assert_safe_json_payload(value: Any, path: str = "payload") -> Dict[str, Any]:
    """
    Ensures inter-agent payloads are strictly plain JSON objects and do not contain
    callable objects, arbitrary code objects, or dangerous code-execution tokens.
    """
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a JSON object (dict).")

    def _walk(node: Any, current_path: str) -> None:
        if callable(node):
            raise ValueError(f"Executable callable disallowed at '{current_path}'.")
        if isinstance(node, (bytes, bytearray)):
            raise ValueError(f"Raw binary payload disallowed at '{current_path}'.")
        if isinstance(node, str):
            lowered = node.lower()
            for token in FORBIDDEN_CODE_PATTERNS:
                if token in lowered:
                    raise ValueError(
                        f"Disallowed executable code pattern '{token}' detected in '{current_path}'."
                    )
        elif isinstance(node, dict):
            for k, v in node.items():
                if not isinstance(k, str):
                    raise ValueError(f"Non-string key disallowed at '{current_path}'.")
                _walk(v, f"{current_path}.{k}")
        elif isinstance(node, (list, tuple)):
            for idx, item in enumerate(node):
                _walk(item, f"{current_path}[{idx}]")
        elif node is not None and not isinstance(node, (int, float, bool)):
            raise ValueError(
                f"Unsupported non-JSON type '{type(node).__name__}' at '{current_path}'."
            )

    _walk(value, path)
    # Round-trip JSON check
    json.dumps(value)
    return value


class AgentTaskInput(BaseModel):
    """Structured JSON input envelope sent by the Orchestrator to a Specialist Agent."""

    task_id: str = Field(..., min_length=3, max_length=128)
    agent_id: str = Field(..., min_length=3, max_length=64)
    stage_name: str = Field(default="general", min_length=2, max_length=64)
    workflow_run_id: Optional[str] = Field(default=None)
    idempotency_key: str = Field(..., min_length=4, max_length=160)
    payload: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    max_retries: int = Field(default=3, ge=0, le=10)

    def __init__(self, **kwargs: Any) -> None:
        payload = kwargs.get("payload", {})
        assert_safe_json_payload(payload, "payload")
        if not kwargs.get("task_id") or not str(kwargs.get("task_id")).strip():
            raise ValueError("task_id is required.")
        if not kwargs.get("agent_id") or not str(kwargs.get("agent_id")).strip():
            raise ValueError("agent_id is required.")
        if not kwargs.get("idempotency_key") or not str(kwargs.get("idempotency_key")).strip():
            raise ValueError("idempotency_key is required.")
        kwargs.setdefault("stage_name", "general")
        kwargs.setdefault("workflow_run_id", None)
        kwargs.setdefault("timeout_seconds", 60)
        kwargs.setdefault("max_retries", 3)
        super().__init__(**kwargs)

    @field_validator("payload")
    @classmethod
    def validate_safe_payload(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        return assert_safe_json_payload(v, "payload")


class AgentTaskOutput(BaseModel):
    """
    Required structured JSON output schema returned by every agent in Step 4:
    - task_id
    - agent_id
    - status
    - result
    - errors
    - started_at
    - completed_at
    - execution_metadata
    """

    task_id: str = Field(..., min_length=3, max_length=128)
    agent_id: str = Field(..., min_length=3, max_length=64)
    status: str = Field(..., description="completed | failed | cancelled | dead_letter | not_connected")
    result: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    started_at: str = Field(...)
    completed_at: str = Field(...)
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **kwargs: Any) -> None:
        required_keys = (
            "task_id",
            "agent_id",
            "status",
            "result",
            "errors",
            "started_at",
            "completed_at",
            "execution_metadata",
        )
        for key in required_keys:
            if key not in kwargs:
                raise ValueError(f"Missing required AgentTaskOutput field: '{key}'")
        assert_safe_json_payload(kwargs["result"], "result")
        assert_safe_json_payload(kwargs["execution_metadata"], "execution_metadata")
        super().__init__(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "result": self.result,
            "errors": list(self.errors),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "execution_metadata": self.execution_metadata,
        }


class AgentConfigurationSpec(BaseModel):
    """
    Runtime configuration and state for each registered agent (Section 6).
    """

    agent_id: str
    slug: str
    name: str
    role: str
    description: str
    is_orchestrator: bool = False
    enabled: bool = True
    provider: str = "unconfigured"
    model: str = "gemini-2.5-pro"
    timeout_seconds: int = 90
    max_retries: int = 3
    temperature: Optional[float] = 0.2
    system_instructions: str = ""
    allow_image_generation: bool = False
    last_execution: Optional[str] = None
    current_status: str = "Idle"  # Running | Idle | Paused | Disabled | Error
    current_task: str = "Standby — awaiting Orchestrator task assignment"
    success_count: int = 0
    failure_count: int = 0

    def __init__(self, **kwargs: Any) -> None:
        defaults = {
            "is_orchestrator": False,
            "enabled": True,
            "provider": "unconfigured",
            "model": "gemini-2.5-pro",
            "timeout_seconds": 90,
            "max_retries": 3,
            "temperature": 0.2,
            "system_instructions": "",
            "allow_image_generation": False,
            "last_execution": None,
            "current_status": "Idle",
            "current_task": "Standby — awaiting Orchestrator task assignment",
            "success_count": 0,
            "failure_count": 0,
        }
        merged = {**defaults, **kwargs}
        super().__init__(**merged)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "slug": self.slug,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "is_orchestrator": self.is_orchestrator,
            "enabled": self.enabled,
            "provider": self.provider,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "temperature": self.temperature,
            "system_instructions": self.system_instructions,
            "allow_image_generation": self.allow_image_generation,
            "last_execution": self.last_execution,
            "current_status": self.current_status,
            "current_task": self.current_task,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
