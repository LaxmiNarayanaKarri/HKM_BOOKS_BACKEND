from typing import List, Optional, Dict, Any

from app.contracts.language_repository import ILanguageRepository
from app.models import Language
from app.injector import DBContract, injector, singleton


TABLE = "languages"


@singleton(ILanguageRepository)
@injector
class SupabaseLanguageRepository(ILanguageRepository):

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
    def _to_model(row: dict) -> Language:
        return Language(
            id=row["id"],
            name=row["name"],
        )

    # ------------------------------------------------------------------
    # ILanguageRepository
    # ------------------------------------------------------------------

    def list_all(self) -> List[Language]:
        resp = (
            self._table
            .select("*")
            .order("name")
            .execute()
        )
        return [self._to_model(r) for r in (resp.data or [])]

    def get(self, language_id: int) -> Optional[Language]:
        resp = (
            self._table
            .select("*")
            .eq("id", language_id)
            .maybe_single()
            .execute()
        )
        return self._to_model(resp.data) if resp.data else None

    def find_by_name(self, name: str) -> Optional[Language]:
        resp = (
            self._table
            .select("*")
            .eq("name", self._normalize(name))
            .maybe_single()
            .execute()
        )
        return self._to_model(resp.data) if resp.data else None

    def add(self, language: Language) -> Language:
        payload = self._serialize({"name": self._normalize(language.name)})
        resp = (
            self._table
            .insert(payload)
            .select()
            .execute()
        )
        if resp is None or not resp.data:
            raise RuntimeError(f"Failed to insert language '{language.name}' — no data returned.")
        return self._to_model(resp.data[0])

    def update(self, language_id: int, **fields) -> Optional[Language]:
        allowed = {"name"}
        payload = self._serialize({k: v for k, v in fields.items() if k in allowed})
        if not payload:
            return self.get(language_id)

        resp = (
            self._table
            .update(payload)
            .eq("id", language_id)
            .select()
            .maybe_single()
            .execute()
        )
        return self._to_model(resp.data) if resp.data else None

    def delete(self, language_id: int) -> bool:
        resp = (
            self._table
            .delete()
            .eq("id", language_id)
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