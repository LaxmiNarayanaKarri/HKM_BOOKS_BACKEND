"""
app/repositories/supabase_inventory_repository.py

Concrete Supabase implementation of IInventoryRepository. Every method
here is one RPC call into a Postgres function that does its DB work in
a single transaction -- see migrations/inventory_atomic_ops.sql. This
class's only job is serializing Python values (dates, etc.) to what the
RPC expects and deserializing the row(s) that come back; no business
rules live here.
"""

from typing import Any, Dict, List, Optional

from app.contracts.inventory_repository import IInventoryRepository
from app.models import Purchase
from app.injector import DBContract, injector, singleton


@singleton(IInventoryRepository)
@injector
class SupabaseInventoryRepository(IInventoryRepository):

    def __init__(self, db: DBContract):
        self.db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_purchase(row: dict) -> Purchase:
        return Purchase(
            id=row.get("id"),
            purchase_date=row.get("purchase_date"),
            book_id=row.get("book_id"),
            source_id=row.get("source_id"),
            qty=row.get("qty"),
            cost_price=row.get("cost_price"),
            recorded_by=row.get("recorded_by"),
            created_at=row.get("created_at"),
        )

    @staticmethod
    def _serialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
        purchase_date = item.get("purchase_date")
        return {
            "book_id": item["book_id"],
            "qty": item["qty"],
            "cost_price": item.get("cost_price"),
            "purchase_date": str(purchase_date) if purchase_date else None,
            "source_id": item.get("source_id"),
            "recorded_by": item.get("recorded_by"),
        }

    @staticmethod
    def _first_row(data) -> Optional[dict]:
        # Postgres functions returning a single row can come back from
        # PostgREST as either a dict or a one-element list depending on
        # client version -- normalize both.
        if data is None:
            return None
        if isinstance(data, list):
            return data[0] if data else None
        return data

    # ------------------------------------------------------------------
    # IInventoryRepository
    # ------------------------------------------------------------------

    def record_inward_batch(self, items: List[dict]) -> List[Purchase]:
        if not items:
            return []

        resp = (
            self.db.get_client()
            .rpc("record_inward_stock_batch", {
                "p_items": [self._serialize_item(i) for i in items],
            })
            .execute()
        )
        if resp is None or resp.data is None:
            raise RuntimeError("record_inward_stock_batch RPC returned no data.")
        return [self._to_purchase(r) for r in resp.data]

    def update_purchase_atomic(self, purchase_id: int, fields: dict) -> Optional[Purchase]:
        payload = dict(fields)
        if "purchase_date" in payload and payload["purchase_date"] is not None:
            payload["purchase_date"] = str(payload["purchase_date"])

        resp = (
            self.db.get_client()
            .rpc("update_purchase_atomic", {
                "p_purchase_id": purchase_id,
                "p_fields": payload,
            })
            .execute()
        )
        row = self._first_row(resp.data if resp is not None else None)
        return self._to_purchase(row) if row else None

    def delete_purchase_atomic(self, purchase_id: int) -> bool:
        resp = (
            self.db.get_client()
            .rpc("delete_purchase_atomic", {"p_purchase_id": purchase_id})
            .execute()
        )
        data = resp.data if resp is not None else None
        if isinstance(data, list):
            data = data[0] if data else None
        return bool(data)