"""
NEXUS MEDIA AI — Authentication API Endpoints
Routes:
- POST /api/auth/login
- GET /api/auth/me
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppSettings, get_settings
from app.database import get_db_session
from app.dependencies import get_current_principal
from app.security.auth import (
    AuthenticatedPrincipal,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: Dict[str, Any]


@router.post("/login", response_model=LoginResponse, summary="Log in with email & password to receive a JWT")
async def login(
    payload: LoginRequest,
    session: Optional[AsyncSession] = Depends(get_db_session),
    settings: AppSettings = Depends(get_settings),
) -> LoginResponse:
    email = payload.email.strip().lower()
    password = payload.password

    user_id = None
    user_roles: List[str] = []
    user_name = "Administrator"

    # 1. Attempt database authentication if session is active
    if session is not None:
        try:
            user_stmt = text(
                "SELECT id, email, full_name, password_hash, status FROM public.users WHERE LOWER(email) = :email LIMIT 1"
            )
            user_result = await session.execute(user_stmt, {"email": email})
            user_row = user_result.mappings().first()

            if user_row and user_row.get("password_hash"):
                if verify_password(password, user_row["password_hash"]):
                    if user_row.get("status") != "active":
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Account is suspended or inactive.",
                        )
                    user_id = str(user_row["id"])
                    user_name = str(user_row.get("full_name") or "Administrator")
                    role_stmt = text("SELECT role_name FROM public.user_roles WHERE user_id = :uid")
                    role_result = await session.execute(role_stmt, {"uid": user_row["id"]})
                    user_roles = [str(r["role_name"]) for r in role_result.mappings().all()]
        except HTTPException:
            raise
        except Exception:
            pass

    # 2. Fallback to environment variable credentials (bootstrap / emergency / dev)
    if user_id is None:
        admin_email = (settings.ADMIN_EMAIL or "").strip().lower()
        admin_pwd_hash = (settings.ADMIN_PASSWORD_HASH or "").strip()
        admin_plain_pwd = (settings.ADMIN_PASSWORD or "").strip()

        if admin_email and email == admin_email:
            valid = False
            if admin_pwd_hash and verify_password(password, admin_pwd_hash):
                valid = True
            elif admin_plain_pwd and password == admin_plain_pwd:
                valid = True

            if valid:
                user_id = "bootstrap-admin-01"
                user_name = "Bootstrap Administrator"
                user_roles = ["super_admin", "operator"]

        # Default fallback in development/test environment if no specific credentials configured
        elif settings.APP_ENV in ("development", "test") and not admin_email:
            if email == "admin@nexusmedia.ai" and password in ("AdminPass123!", "ChangeMe123!"):
                user_id = "default-admin-01"
                user_name = "Default Administrator"
                user_roles = ["super_admin", "operator"]

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_roles:
        user_roles = ["super_admin"]

    token = create_access_token(
        user_id=user_id,
        email=email,
        roles=user_roles,
        settings=settings,
        expires_delta_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user={
            "id": user_id,
            "email": email,
            "name": user_name,
            "roles": user_roles,
        },
    )


@router.get("/me", summary="Get currently authenticated user details")
async def get_me(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> Dict[str, Any]:
    return {
        "user_id": principal.user_id,
        "email": principal.email,
        "roles": principal.roles,
        "session_id": principal.session_id,
    }
