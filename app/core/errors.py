"""
Central place mapping domain exceptions to HTTP responses.

The old Flask routes each wrapped their controller call in a
`try/except ValidationError: flash(str(exc), "error")`. In a pure JSON
API there's no flash message to render, so this registers one
exception handler on the app instead -- every router can just let
`ValidationError` propagate and it becomes a `400` with the same
message as its `detail`.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.books_domain import ValidationError

class ValidationError(Exception):
    """Input failed a business rule (bad password length, duplicate
    username, missing field, ...)."""


class AuthError(Exception):
    """Credentials were wrong, or the account can't sign in right now."""


class NotFoundError(Exception):
    """Referenced a username that doesn't exist."""


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(AuthError, auth_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)

