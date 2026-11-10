"""
NEXUS MEDIA AI — AI Agent Registry, Orchestrator & Control Center Endpoints (Step 3 & Step 4)
Routes:
- GET /api/agents
- GET /api/agents/orchestrator/status
- GET /api/agents/{agent_id}
- GET /api/agents/{agent_id}/details
- GET /api/agents/{agent_id}/history
- POST /api/agents/{agent_id}/enable
- POST /api/agents/{agent_id}/disable
- POST /api/agents/{agent_id}/pause
- POST /api/agents/{agent_id}/resume
- PATCH /api/agents/{agent_id}/config
- POST /api/agents/tasks/{task_id}/cancel
- POST /api/agents/workflows/run
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import orchestrator_engine
from app.database import get_db_session
from app.dependencies import (
    PaginationParams,
    get_pagination,
    require_admin,
    require_operator_or_admin,
)
from app.schemas.payloads import (
    AgentActionRequest,
    AgentActionResponse,
    AgentConfigUpdateRequest,
    AgentItemSchema,
    AgentListResponse,
    PaginationMeta,
    WorkflowRunRequest,
)
from app.security.auth import AuthenticatedPrincipal
from app.services.operations import (
    DatabaseUnavailableError,
    get_agent_by_id_service,
    list_agents_service,
    resolve_db_status,
    set_agent_Lifecycle_state_service,
)

router = APIRouter(prefix="/api/agents", tags=["AI Agents & Orchestrator"])


@router.get("", response_model=AgentListResponse, summary="List registered AI agents")
async def list_agents(
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by agent status"),
    pagination: PaginationParams = Depends(get_pagination),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> AgentListResponse:
    items, total, db_status = await list_agents_service(
        session=session,
        offset=pagination.offset,
        limit=pagination.page_size,
        status_filter=status_filter,
    )
    return AgentListResponse(
        items=[AgentItemSchema(**item) for item in items],
        pagination=PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total,
        ),
        database_status=db_status,
        orchestrator_summary=orchestrator_engine.get_system_overview(),
    )


@router.get(
    "/orchestrator/status",
    summary="Get Central Orchestrator & 9 Specialist Agents Control Center status",
)
async def get_orchestrator_status() -> Dict[str, Any]:
    db_status = await resolve_db_status()
    overview = orchestrator_engine.get_system_overview()
    return {
        "database_status": db_status,
        "agents": orchestrator_engine.list_all_agents(),
        **overview,
    }


@router.get("/{agent_id}", response_model=AgentItemSchema, summary="Get single AI agent telemetry")
async def get_agent(
    agent_id: str,
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> AgentItemSchema:
    agent, db_status = await get_agent_by_id_service(session=session, agent_id=agent_id)
    if db_status != "connected":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": f"Cannot query persisted agent '{agent_id}' while database is '{db_status}'.",
                "database_status": db_status,
            },
        )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": f"Agent '{agent_id}' was not found."},
        )
    return AgentItemSchema(**agent)


@router.get(
    "/{agent_id}/details",
    summary="Get full Step 4 agent configuration, provider status, and execution history",
)
async def get_agent_control_details(agent_id: str) -> Dict[str, Any]:
    try:
        db_status = await resolve_db_status()
        details = orchestrator_engine.get_agent_details(agent_id)
        return {
            "database_status": db_status,
            "agent": details,
        }
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.get(
    "/{agent_id}/history",
    summary="Get structured execution logs and task history for a specific agent",
)
async def get_agent_execution_history(agent_id: str) -> Dict[str, Any]:
    try:
        details = orchestrator_engine.get_agent_details(agent_id)
        return {
            "agent_id": details["agent_id"],
            "name": details["name"],
            "execution_history": details["execution_history"],
            "recent_tasks": details["recent_tasks"],
        }
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.post(
    "/{agent_id}/enable",
    response_model=AgentActionResponse,
    summary="Enable an AI agent (Operator or Admin role required)",
)
async def enable_agent(
    agent_id: str,
    payload: Optional[AgentActionRequest] = None,
    principal: AuthenticatedPrincipal = Depends(require_operator_or_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> AgentActionResponse:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": f"Cannot persist enable state for '{agent_id}' while database is not configured.",
            },
        )
    try:
        res = orchestrator_engine.set_agent_state(
            agent_id,
            action="enable",
            actor=principal.sub,
            reason=payload.reason if payload else None,
        )
        return AgentActionResponse(**res)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.post(
    "/{agent_id}/disable",
    response_model=AgentActionResponse,
    summary="Disable an AI agent (Operator or Admin role required)",
)
async def disable_agent(
    agent_id: str,
    payload: Optional[AgentActionRequest] = None,
    principal: AuthenticatedPrincipal = Depends(require_operator_or_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> AgentActionResponse:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": f"Cannot persist disable state for '{agent_id}' while database is not configured.",
            },
        )
    try:
        res = orchestrator_engine.set_agent_state(
            agent_id,
            action="disable",
            actor=principal.sub,
            reason=payload.reason if payload else None,
        )
        return AgentActionResponse(**res)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.post(
    "/{agent_id}/pause",
    response_model=AgentActionResponse,
    summary="Pause an AI agent (Operator or Admin role required)",
)
async def pause_agent(
    agent_id: str,
    payload: Optional[AgentActionRequest] = None,
    principal: AuthenticatedPrincipal = Depends(require_operator_or_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> AgentActionResponse:
    try:
        result = await set_agent_Lifecycle_state_service(
            session=session,
            agent_id=agent_id,
            target_status="paused",
            actor_sub=principal.sub,
            reason=payload.reason if payload else None,
        )
        return AgentActionResponse(**result)
    except DatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_UNAVAILABLE", "message": exc.message},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.post(
    "/{agent_id}/resume",
    response_model=AgentActionResponse,
    summary="Resume a paused AI agent (Operator or Admin role required)",
)
async def resume_agent(
    agent_id: str,
    payload: Optional[AgentActionRequest] = None,
    principal: AuthenticatedPrincipal = Depends(require_operator_or_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> AgentActionResponse:
    try:
        result = await set_agent_Lifecycle_state_service(
            session=session,
            agent_id=agent_id,
            target_status="running",
            actor_sub=principal.sub,
            reason=payload.reason if payload else None,
        )
        return AgentActionResponse(**result)
    except DatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_UNAVAILABLE", "message": exc.message},
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.patch(
    "/{agent_id}/config",
    summary="Update AI agent model, timeout, retries, temperature, and instructions (Admin role required)",
)
async def update_agent_configuration(
    agent_id: str,
    payload: AgentConfigUpdateRequest,
    principal: AuthenticatedPrincipal = Depends(require_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> Dict[str, Any]:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": f"Cannot persist configuration changes for '{agent_id}' while database is not configured.",
            },
        )
    try:
        updated = orchestrator_engine.update_agent_config(
            agent_id,
            updates=payload.model_dump(exclude_none=True),
            actor=principal.sub,
        )
        return {"status": "updated", "agent": updated}
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_AGENT_CONFIG", "message": str(exc)},
        ) from exc


@router.post(
    "/tasks/{task_id}/cancel",
    summary="Cancel a queued or running agent task (Operator or Admin role required)",
)
async def cancel_agent_task(
    task_id: str,
    payload: Optional[AgentActionRequest] = None,
    principal: AuthenticatedPrincipal = Depends(require_operator_or_admin),
) -> Dict[str, Any]:
    try:
        record = orchestrator_engine.task_queue.cancel_task(
            task_id,
            reason=(payload.reason if payload and payload.reason else f"Cancelled by {principal.sub}"),
        )
        return {"status": "cancelled", "task": record.to_dict()}
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": str(exc)},
        ) from exc


@router.post(
    "/workflows/run",
    summary="Dispatch a 10-stage Orchestrator workflow run (Operator or Admin role required)",
)
async def trigger_orchestrator_workflow(
    payload: WorkflowRunRequest,
    principal: AuthenticatedPrincipal = Depends(require_operator_or_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> Dict[str, Any]:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": "Cannot execute production workflow run while Supabase database is not configured.",
            },
        )
    result = await orchestrator_engine.run_workflow_pipeline(
        idempotency_key=payload.idempotency_key,
        topic_headline=payload.topic_headline,
        sources=payload.sources,
        feed_items=payload.feed_items,
        candidate_images=payload.candidate_images,
        analytics_connected=payload.analytics_connected,
    )
    return result
