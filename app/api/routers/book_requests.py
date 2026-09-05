from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import get_book_requests_controller
from app.controllers.book_requests_controller import BookRequestsController
from app.core.auth import CurrentUser, require_permission
from app.models import BookRequest

router = APIRouter(prefix="/api/book-requests", tags=["book-requests"])


class BookRequestCreate(BaseModel):
    book_id: int
    quantity: int = Field(gt=0)
    location_id: int
    event_id: int
    priority: str


@router.post("", status_code=201)
def create_book_request(
    payload: BookRequestCreate,
    user: CurrentUser = Depends(require_permission("book_request_create")),
    controller: BookRequestsController = Depends(get_book_requests_controller),
):
    if payload.priority not in {"cant_wait", "important", "immediate"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid request priority.")
    return controller.create(
        BookRequest(
            book_id=payload.book_id,
            quantity=payload.quantity,
            location_id=payload.location_id,
            event_id=payload.event_id,
            priority=payload.priority,
            requested_by=user.username,
        )
    )


@router.get("/mine")
def list_my_book_requests(
    limit: int = Query(default=200, ge=1, le=500),
    user: CurrentUser = Depends(require_permission("book_request_create")),
    controller: BookRequestsController = Depends(get_book_requests_controller),
):
    return controller.list_for_user(user.username)[:limit]


@router.get("/history")
def list_book_request_history(
    limit: int = Query(default=500, ge=1, le=1000),
    user: CurrentUser = Depends(require_permission("book_request_history")),
    controller: BookRequestsController = Depends(get_book_requests_controller),
):
    return controller.list_all()[:limit]


@router.post("/{request_id}/approve")
def approve_book_request(
    request_id: str,
    user: CurrentUser = Depends(require_permission("book_request_history")),
    controller: BookRequestsController = Depends(get_book_requests_controller),
):
    return controller.approve(request_id)
