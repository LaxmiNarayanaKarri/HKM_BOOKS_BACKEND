# dependencies/auth.py
import secrets
import os
from fastapi import Header, HTTPException, status


async def verify_internal_token(
    x_internal_token: str = Header(..., alias="X-Internal-Token"),
) -> None:
    internal_token = os.environ.get("INTERNAL_SERVICE_TOKEN", "")
    if not secrets.compare_digest(x_internal_token, internal_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal service token",
        )