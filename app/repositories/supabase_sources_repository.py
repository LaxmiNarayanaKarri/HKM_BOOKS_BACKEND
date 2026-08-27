from typing import List, Optional, Dict, Any

from app.contracts.source_repository import ISourceRepository
from app.models import Source
from app.injector import DBContract, injector, singleton


TABLE = "sources"


@singleton(ISourceRepository)
@injector
class SupabaseSourceRepository(ISourceRepository):

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
    def _to_model(row: dict) -> Source:
        return Source(
            id=row["id"],
            name=row["name"],
        )

    # ------------------------------------------------------------------
    # ISourceRepository
    # ------------------------------------------------------------------

    def list_all(self) -> List[Source]:
        resp = (
            self._table
            .select("*")
            .order("name")
            .execute()
        )
        return [self._to_model(r) for r in (resp.data or [])]

    def get(self, source_id: int) -> Optional[Source]:
        resp = (
            self._table
            .select("*")
            .eq("id", source_id)
            .maybe_single()
            .execute()
        )
        return self._to_model(resp.data) if resp.data else None

    def find_by_name(self, name: str) -> Optional[Source]:
        resp = (
            self._table
            .select("*")
            .eq("name", self._normalize(name))
            .maybe_single()
            .execute()
        )
        return self._to_model(resp.data) if resp.data else None

    def add(self, source: Source) -> Source:
        payload = self._serialize({"name": self._normalize(source.name)})
        resp = (
            self._table
            .insert(payload)
            .select()
            .execute()
        )
        if resp is None or not resp.data:
            raise RuntimeError(f"Failed to insert source '{source.name}' — no data returned.")
        return self._to_model(resp.data[0])

    def update(self, source_id: int, **fields) -> Optional[Source]:
        allowed = {"name"}
        payload = self._serialize({k: v for k, v in fields.items() if k in allowed})
        if not payload:
            return self.get(source_id)

        resp = (
            self._table
            .update(payload)
            .eq("id", source_id)
            .select()
            .maybe_single()
            .execute()
        )
        return self._to_model(resp.data) if resp.data else None

    def delete(self, source_id: int) -> bool:
        resp = (
            self._table
            .delete()
            .eq("id", source_id)
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