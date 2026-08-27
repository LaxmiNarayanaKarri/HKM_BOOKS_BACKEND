"""
FastAPI authentication dependencies.

Identity resolution order
--------------------------
1.  `X-Internal-Secret` header -- pod-to-pod calls from the Users service.
    Checked against INTERNAL_SECRET env var.  Resolves to a synthetic
    service identity (role="service") so domain code never needs to know
    whether the caller is a human or another pod.

2.  `Authorization: Bearer <token>` -- Supabase JWT for real user sessions.

3.  `X-User` / `X-Role` headers -- local dev / curl testing escape hatch.
    Strip these at the ingress in production.

Required env vars
-----------------
    SUPABASE_JWT_SECRET  -- Supabase Dashboard → Settings → API → JWT Secret
    INTERNAL_SECRET      -- shared with every pod that calls this service;
                           generate with: openssl rand -hex 32
"""

import os
import secrets
from dataclasses import dataclass
from typing import Optional

import jwt  # PyJWT
from fastapi import Depends, Header, HTTPException, status

_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "").strip()
_JWT_ALGORITHMS = ["HS256"]

_INTERNAL_SECRET = os.environ.get("INTERNAL_SECRET", "").strip()


@dataclass
class CurrentUser:
    username: str
    role: str = "user"
    id: Optional[int] = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_service(self) -> bool:
        """True when the caller is another internal pod, not a human user."""
        return self.role == "service"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _user_from_internal_secret(header_value: Optional[str]) -> Optional[CurrentUser]:
    """Authenticate a pod-to-pod call via the shared INTERNAL_SECRET."""
    if not header_value or not _INTERNAL_SECRET:
        return None
    # Constant-time comparison -- avoids timing side-channel on the secret.
    if not secrets.compare_digest(header_value, _INTERNAL_SECRET):
        return None
    return CurrentUser(username="internal-service", role="service")


def _user_from_bearer(token: str) -> Optional[CurrentUser]:
    """Decode a Supabase JWT and return a CurrentUser, or None on any failure."""
    if not _JWT_SECRET:
        return None
    try:
        payload = jwt.decode(
            token,
            _JWT_SECRET,
            algorithms=_JWT_ALGORITHMS,
            options={"verify_aud": False},
        )
        username: str = payload.get("sub") or payload.get("email") or ""
        if not username:
            return None
        role: str = payload.get("role", "user").lower()

        # Supabase JWTs carry the user's UUID in `sub`. If this service's
        # domain model uses an integer id, that id is typically stashed in
        # user_metadata / app_metadata (or a custom claim) rather than `sub`
        # itself. Try the common spots and fall back to None if not present.
        raw_id = (
            payload.get("id")
            or payload.get("user_id")
            or (payload.get("app_metadata") or {}).get("id")
            or (payload.get("user_metadata") or {}).get("id")
        )
        user_id: Optional[int] = None
        if raw_id is not None:
            try:
                user_id = int(raw_id)
            except (TypeError, ValueError):
                user_id = None

        return CurrentUser(username=username, role=role, id=user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except jwt.InvalidTokenError:
        return None


def _user_from_headers(
    x_user: Optional[str],
    x_role: Optional[str],
    x_user_id: Optional[str],
) -> Optional[CurrentUser]:
    if not x_user:
        return None
    user_id: Optional[int] = None
    if x_user_id is not None:
        try:
            user_id = int(x_user_id)
        except ValueError:
            user_id = None
    return CurrentUser(username=x_user, role=(x_role or "user").lower(), id=user_id)


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

def get_current_user(
    x_internal_secret: Optional[str] = Header(default=None, alias="X-Internal-Secret"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_user: Optional[str] = Header(default=None, alias="X-User"),
    x_role: Optional[str] = Header(default=None, alias="X-Role"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
) -> CurrentUser:
    # 1. Internal pod-to-pod secret (highest priority)
    user = _user_from_internal_secret(x_internal_secret)
    if user:
        return user

    # 2. Bearer JWT (production browser sessions)
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[len("bearer "):]
        user = _user_from_bearer(token)
        if user:
            return user
        # Token present but invalid -- don't fall through
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    # 3. X-User / X-Role / X-User-Id dev headers
    user = _user_from_headers(x_user, x_role, x_user_id)
    if user:
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
    )


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return user