"""JWT/API-token auth helpers and RBAC checks for API routes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request

try:
    import jwt
    from jwt import InvalidTokenError
except Exception:  # pragma: no cover - optional dependency in some local setups
    jwt = None
    InvalidTokenError = Exception


@dataclass(frozen=True)
class AuthContext:
    """Authenticated request context used by API handlers."""

    subject: str
    roles: set[str]
    raw_claims: dict[str, Any]

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


def get_configured_auth_mode() -> str:
    """
    Resolve auth mode based on environment.

    - `jwt`: when JWT_SECRET is configured.
    - `token`: when API_BEARER_TOKEN is configured.
    - `none`: no auth configured (local development only).
    """
    if os.getenv("JWT_SECRET", "").strip():
        return "jwt"
    if os.getenv("API_BEARER_TOKEN", "").strip():
        return "token"
    return "none"


def _extract_roles(claims: dict[str, Any]) -> set[str]:
    roles: set[str] = set()
    raw_roles = claims.get("roles")
    if isinstance(raw_roles, list):
        roles.update(str(item).strip() for item in raw_roles if str(item).strip())
    elif isinstance(raw_roles, str):
        roles.update(part.strip() for part in raw_roles.split(",") if part.strip())

    raw_scope = claims.get("scope")
    if isinstance(raw_scope, str):
        roles.update(part.strip() for part in raw_scope.split() if part.strip())
    return roles


def _decode_jwt(token: str) -> AuthContext:
    if jwt is None:
        raise HTTPException(
            status_code=500,
            detail="PyJWT is required for JWT authentication mode.",
        )
    secret = os.getenv("JWT_SECRET", "").strip()
    algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip() or "HS256"
    audience = os.getenv("JWT_AUDIENCE", "").strip() or None
    issuer = os.getenv("JWT_ISSUER", "").strip() or None
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            audience=audience,
            issuer=issuer,
            options={"require": ["sub", "exp"]},
        )
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired JWT.") from exc
    sub = str(claims.get("sub", "")).strip()
    if not sub:
        raise HTTPException(status_code=401, detail="JWT subject (sub) is required.")
    return AuthContext(subject=sub, roles=_extract_roles(claims), raw_claims=claims)


def authenticate_request(request: Request) -> AuthContext | None:
    """
    Authenticate API request from Authorization header.

    Returns `None` when auth mode is disabled.
    """
    mode = get_configured_auth_mode()
    if mode == "none":
        return None

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    if mode == "token":
        expected = os.getenv("API_BEARER_TOKEN", "").strip()
        if token != expected:
            raise HTTPException(status_code=401, detail="Invalid bearer token.")
        return AuthContext(subject="service-token", roles={"admin"}, raw_claims={})

    return _decode_jwt(token)


def require_roles(auth: AuthContext | None, required: set[str]) -> None:
    """Raise 403 if the auth context does not satisfy required roles."""
    if not required:
        return
    if auth is None:
        raise HTTPException(status_code=401, detail="Authentication is required.")
    if auth.is_admin:
        return
    if not required.intersection(auth.roles):
        needed = ", ".join(sorted(required))
        raise HTTPException(status_code=403, detail=f"Missing required role. Need one of: {needed}")
