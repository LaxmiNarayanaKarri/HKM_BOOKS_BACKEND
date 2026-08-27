"""
app/repositories/supabase_stock_repository.py

Concrete Supabase implementation of IStockRepository, mirroring
SupabaseCategoryRepository. upsert_batch calls a Postgres function
(adjust_stock_batch, see migrations/inventory_atomic_ops.sql) so the
whole batch of stock rows commits or rolls back together -- but note
this is scoped to the stock table only (see module docstring in
stock_repository.py for why that's not enough for record_inward_stock).
"""

from typing import Any, Dict, List, Optional

from app.contracts.stock_repository import IStockRepository, StockDelta
from app.models import Stock
from app.injector import DBContract, injector, singleton


TABLE = "stock"


@singleton(IStockRepository)
@injector
class SupabaseStockRepository(IStockRepository):

    def __init__(self, db: DBContract):
        self.db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _table(self):
        return self.db.get_client().table(TABLE)

    @staticmethod
    def _serialize(fields: Dict[str, Any], *, drop_none_id: bool = False) -> Dict[str, Any]:
        out = dict(fields)
        if drop_none_id and out.get("id") is None:
            out.pop("id", None)
        return out

    @staticmethod
    def _to_model(row: dict) -> Stock:
        return Stock(
            id=row["id"],
            book_id=row.get("book_id"),
            stock=row.get("stock"),
            cost=row.get("cost"),
        )

    # ------------------------------------------------------------------
    # IStockRepository
    # ------------------------------------------------------------------

    def list_all(self) -> List[Stock]:
        resp = self._table.select("*").order("id").execute()
        return [self._to_model(r) for r in (resp.data or [])]

    def get(self, stock_id: int) -> Optional[Stock]:
        resp = self._table.select("*").eq("id", stock_id).maybe_single().execute()
        return self._to_model(resp.data) if resp.data else None

    def get_by_book_id(self, book_id: int) -> Optional[Stock]:
        resp = self._table.select("*").eq("book_id", book_id).maybe_single().execute()
        return self._to_model(resp.data) if resp.data else None

    def add(self, stock: Stock) -> Stock:
        payload = self._serialize({
            "book_id": stock.book_id,
            "stock": stock.stock,
            "cost": stock.cost,
        })
        resp = self._table.insert(payload).select().execute()
        if resp is None or not resp.data:
            raise RuntimeError(
                f"Failed to insert stock row for book_id {stock.book_id} — no data returned."
            )
        return self._to_model(resp.data[0])

    def update(self, stock_id: int, **fields) -> Optional[Stock]:
        allowed = {"book_id", "stock", "cost"}
        payload = self._serialize({k: v for k, v in fields.items() if k in allowed})
        if not payload:
            return self.get(stock_id)

        resp = (
            self._table
            .update(payload)
            .eq("id", stock_id)
            .select()
            .maybe_single()
            .execute()
        )
        return self._to_model(resp.data) if resp.data else None

    def delete(self, stock_id: int) -> bool:
        resp = self._table.delete().eq("id", stock_id).execute()
        return bool(resp.data)

    def upsert_batch(self, deltas: List[StockDelta]) -> List[Stock]:
        if not deltas:
            return []

        resp = (
            self.db.get_client()
            .rpc("adjust_stock_batch", {
                "p_deltas": [{"book_id": d.book_id, "delta": d.delta} for d in deltas],
            })
            .execute()
        )
        if resp is None or resp.data is None:
            raise RuntimeError("adjust_stock_batch RPC returned no data.")
        return [self._to_model(r) for r in resp.data]