from typing import List, Optional, Dict, Any

from app.contracts.event_repository import IEventRepository
from app.models import Event
from app.injector import DBContract, injector, singleton


TABLE = "events"


@singleton(IEventRepository)
@injector
class SupabaseEventRepository(IEventRepository):

    def __init__(self, db: DBContract):
        self.db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _table(self):
        return self.db.get_client().table(TABLE)

    @staticmethod
    def _normalize(name: str) -> str:
        return (name or "").strip()

    @staticmethod
    def _serialize(fields: Dict[str, Any], *, drop_none_id: bool = False) -> Dict[str, Any]:
        out = dict(fields)
        if drop_none_id and out.get("id") is None:
            out.pop("id", None)
        return out

    @staticmethod
    def _to_model(row: dict) -> Event:
        return Event(
            id=row["id"],
            name=row["name"],
        )

    # ------------------------------------------------------------------
    # IEventRepository
    # ------------------------------------------------------------------

    def list_all(self) -> List[Event]:
        resp = (
            self._table
            .select("*")
            .order("name")
            .execute()
        )
        return [self._to_model(r) for r in (resp.data or [])]

    def get(self, event_id: int) -> Optional[Event]:
        resp = (
            self._table
            .select("*")
            .eq("id", event_id)
            .maybe_single()
            .execute()
        )
        return self._to_model(resp.data) if resp.data else None

    def find_by_name(self, name: str) -> Optional[Event]:
        resp = (
            self._table
            .select("*")
            .eq("name", self._normalize(name))
            .maybe_single()
            .execute()
        )
        print(resp, name)
        return self._to_model(resp.data) if resp.data else None

    def add(self, event: Event) -> Event:
        payload = self._serialize({"name": self._normalize(event.name)})
        resp = (
            self._table
            .insert(payload)
            .select()
            .execute()
        )
        if resp is None or not resp.data:
            raise RuntimeError(f"Failed to insert event '{event.name}' — no data returned.")
        return self._to_model(resp.data[0])

    def update(self, event_id: int, **fields) -> Optional[Event]:
        allowed = {"name"}
        payload = self._serialize({k: v for k, v in fields.items() if k in allowed})
        if not payload:
            return self.get(event_id)

        resp = (
            self._table
            .update(payload)
            .eq("id", event_id)
            .select()
            .maybe_single()
            .execute()
        )
        return self._to_model(resp.data) if resp.data else None

    def delete(self, event_id: int) -> bool:
        resp = (
            self._table
            .delete()
            .eq("id", event_id)
            .execute()
        )
        return bool(resp.data)

    def name_available(self, name: str) -> bool:
        try:
            resp = (
                self._table
                .select("id")
                .eq("name", self._normalize(name))
                .maybe_single()
                .execute()
            )
            return resp is None or resp.data is None
        except Exception:
            return True