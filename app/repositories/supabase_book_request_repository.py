from datetime import datetime, timezone
from typing import Any, Dict, List

from app.contracts.book_request_repository import IBookRequestRepository
from app.injector import DBContract, injector, singleton
from app.models import BookRequest

TABLE = "book_requests"


@singleton(IBookRequestRepository)
@injector
class SupabaseBookRequestRepository(IBookRequestRepository):
    def __init__(self, db: DBContract):
        self.db = db

    @property
    def table(self):
        return self.db.get_client().table(TABLE)

    @staticmethod
    def _to_model(row: Dict[str, Any]) -> BookRequest:
        return BookRequest(
            id=row["id"],
            book_id=row["book_id"],
            quantity=row["quantity"],
            location_id=row["location_id"],
            event_id=row["event_id"],
            priority=row["priority"],
            requested_by=row["requested_by"],
            status=row.get("status", "pending"),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def create(self, request: BookRequest) -> BookRequest:
        payload = {
            "book_id": request.book_id,
            "quantity": request.quantity,
            "location_id": request.location_id,
            "event_id": request.event_id,
            "priority": request.priority,
            "requested_by": request.requested_by,
            "status": request.status,
            "created_at": request.created_at.isoformat(),
        }
        response = self.table.insert(payload).select().execute()
        return self._to_model(response.data[0])

    def list_for_user(self, username: str, limit: int = 200) -> List[BookRequest]:
        response = self.table.select("*").eq("requested_by", username).order(
            "created_at", desc=True
        ).limit(limit).execute()
        return [self._to_model(row) for row in (response.data or [])]

    def list_all(self, limit: int = 500) -> List[BookRequest]:
        response = self.table.select("*").order("created_at", desc=True).limit(limit).execute()
        return [self._to_model(row) for row in (response.data or [])]

    def update_status(self, request_id: str, status: str) -> BookRequest:
        response = self.table.update({"status": status}).eq("id", request_id).execute()
        rows = response.data or []
        return self._to_model(rows[0]) if rows else None
