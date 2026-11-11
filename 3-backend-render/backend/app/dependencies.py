"""FastAPI dependencies for authentication, RBAC, pagination, and database sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from fastapi import Depends, Header, HTTPException, Query, status

from app.config import AppSettings, get_settings
from app.security.auth import (
    ADMIN_ROLES,
    EDITORIAL_ROLES,
    OPERATOR_ROLES,
    AuthenticatedPrincipal,
    decode_and_verify_access_token,
)


@dataclass(frozen=True)
class PaginationParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def get_pagination(
    page: int = Query(default=1, ge=1, le=1000, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


def get_current_principal(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    settings: AppSettings = Depends(get_settings),
) -> AuthenticatedPrincipal:
    """Enforces Bearer token authentication with zero insecure bypasses."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[len("Bearer ") :].strip()
    try:
        return decode_and_verify_access_token(token, settings=settings)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_roles(allowed_roles: Iterable[str]) -> Callable[[AuthenticatedPrincipal], AuthenticatedPrincipal]:
    allowed = tuple(allowed_roles)

    def _dependency(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
    ) -> AuthenticatedPrincipal:
        if not principal.has_any_role(allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {', '.join(allowed)}.",
            )
        return principal

    return _dependency


require_admin = require_roles(ADMIN_ROLES)
require_operator_or_admin = require_roles(OPERATOR_ROLES)
require_editor_or_admin = require_roles(EDITORIAL_ROLES)


def get_optional_principal(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    settings: AppSettings = Depends(get_settings),
) -> Optional[AuthenticatedPrincipal]:
    """Extracts principal if valid Authorization header present, else None without aborting."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[len("Bearer ") :].strip()
    try:
        return decode_and_verify_access_token(token, settings=settings)
    except Exception:
        return None
