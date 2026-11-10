"""
NEXUS MEDIA AI — System Control & Emergency Kill Switch Endpoints
Routes:
- GET /api/system/kill-switch
- POST /api/system/kill-switch
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import require_operator_or_admin
from app.security.auth import AuthenticatedPrincipal
from app.services.operations import get_kill_switch_service, set_kill_switch_service

router = APIRouter(prefix="/api/system", tags=["System Control"])


class KillSwitchRequest(BaseModel):
    engaged: bool
    reason: Optional[str] = None


@router.get("/kill-switch", summary="Get global emergency stop / kill switch status")
async def get_kill_switch_status(
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> Dict[str, Any]:
    engaged = await get_kill_switch_service(session)
    return {
        "kill_switch_engaged": engaged,
        "status": "engaged" if engaged else "disengaged",
        "description": "Global emergency kill switch: when engaged, halts all automatic publishing and agent tasks.",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/kill-switch", summary="Engage or disengage global emergency stop (Operator/Admin)")
async def update_kill_switch_status(
    payload: KillSwitchRequest,
    principal: AuthenticatedPrincipal = Depends(require_operator_or_admin),
    session: Optional[AsyncSession] = Depends(get_db_session),
) -> Dict[str, Any]:
    result = await set_kill_switch_service(
        session=session,
        enabled=payload.engaged,
        actor_sub=principal.sub,
        reason=payload.reason,
    )
    return {
        "kill_switch_engaged": result["kill_switch_enabled"],
        "status": "engaged" if result["kill_switch_enabled"] else "disengaged",
        "updated_by": result["updated_by"],
        "reason": result["reason"],
        "source": result["source"],
        "timestamp": result["timestamp"].isoformat(),
    }
