"""
Injected data-access boundary + all Purchases business logic, mirroring
`app/domain/locations_domain.py`.

Every write here goes through `inventory` (IInventoryRepository), not
`repo`. A purchase row always implies a stock claim -- creating one
means stock went up, editing qty/book_id means stock should move by the
delta, deleting one means stock should give that quantity back. Doing
those as two separate REST calls (purchases repo, then a stock repo)
can't be made atomic from the app side -- a failure between the two
calls leaves purchases and stock permanently out of sync, and there's
no way to "un-happen" the first call if the second one fails partway.
So `repo` (IPurchaseRepository) is kept only for reads; every mutation
is one call into `inventory`, which runs as a single Postgres
transaction (see migrations/inventory_atomic_ops.sql).
"""

from datetime import date
from typing import List, Optional

from app.contracts.inventory_repository import IInventoryRepository
from app.contracts.purchase_repository import IPurchaseRepository
from app.injector import injector
from app.models import Purchase


@injector
class PurchasesDomain:
    """
    `repo` is auto-injected against `IPurchaseRepository` for reads.
    `inventory` is auto-injected against `IInventoryRepository` for
    every write, since those all have to move stock atomically too.
    Neither is referenced concretely here -- either can be swapped for
    a fake in tests.
    """

    def __init__(self, repo: IPurchaseRepository, inventory: IInventoryRepository):
        self.repo = repo
        self.inventory = inventory

    # ------------------------------------------------------------------
    # Reads -- unchanged, no stock involved
    # ------------------------------------------------------------------

    def list_purchases(self) -> List[Purchase]:
        return self.repo.list_all()

    def get_purchase(self, purchase_id: int) -> Optional[Purchase]:
        return self.repo.get(purchase_id)

    def find_by_short_title(self, short_title: str) -> Optional[Purchase]:
        return self.repo.find_by_name(short_title)

    def recent_purchases(
        self,
        *,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        recorded_by: Optional[str] = None,
        book_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Purchase]:
        """
        Filtered feed backing both the inward-stock page and the
        /export endpoint, so both stay in sync on filtering behaviour.
        """
        return self.repo.list_filtered(
            date_from=date_from,
            date_to=date_to,
            recorded_by=recorded_by,
            book_id=book_id,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Writes -- all atomic with the matching stock change
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_new_purchase(p: Purchase) -> None:
        if p.book_id is None:
            raise ValueError("book_id is required.")
        if p.qty is None or p.qty <= 0:
            raise ValueError("Purchase quantity must be greater than zero.")
        if p.cost_price is None or p.cost_price < 0:
            raise ValueError("Purchase cost price is required and cannot be negative.")

    @staticmethod
    def _as_item(p: Purchase) -> dict:
        return {
            "book_id": p.book_id,
            "qty": p.qty,
            "cost_price": p.cost_price,
            "purchase_date": p.purchase_date,
            "source_id": p.source_id,
            "recorded_by": p.recorded_by,
        }

    def record_purchase(self, purchase: Purchase) -> Purchase:
        self._validate_new_purchase(purchase)
        inserted = self.inventory.record_inward_batch([self._as_item(purchase)])
        return inserted[0]

    def record_batch(self, purchases: List[Purchase]) -> List[Purchase]:
        """
        Invalid rows are dropped (same behaviour as before); the valid
        ones are inserted -- and their stock applied -- together in one
        atomic call, not row by row.
        """
        valid = [
            p for p in purchases
            if p.book_id is not None
            and p.qty and p.qty > 0
            and p.cost_price is not None and p.cost_price >= 0
        ]
        if not valid:
            return []
        return self.inventory.record_inward_batch([self._as_item(p) for p in valid])

    # -- POST /api/inward-stock ----------------------------------------------
    def record_inward_stock(self, user_name: str, payload) -> int:
        if not payload.items:
            raise ValueError("At least one item is required.")

        items = []
        for item in payload.items:
            if item.book_id is None:
                raise ValueError("book_id is required for every item.")
            if item.qty is None or item.qty <= 0:
                raise ValueError(f"qty must be positive for book_id {item.book_id}.")
            if item.cost_price is not None and item.cost_price < 0:
                raise ValueError(f"cost_price cannot be negative for book_id {item.book_id}.")
            items.append({
                "book_id": item.book_id,
                "qty": item.qty,
                "cost_price": item.cost_price,
                "purchase_date": payload.purchase_date,
                "source_id": payload.source_id,
                "recorded_by": user_name,
            })

        inserted = self.inventory.record_inward_batch(items)
        return len(inserted)

    def update_purchase(self, purchase_id: int, **fields) -> Optional[Purchase]:
        allowed = {"book_id", "qty", "cost_price", "purchase_date", "source_id", "recorded_by"}
        payload = {k: v for k, v in fields.items() if k in allowed}

        if "qty" in payload and (payload["qty"] is None or payload["qty"] <= 0):
            raise ValueError("qty must be positive.")
        if "cost_price" in payload and payload["cost_price"] is not None and payload["cost_price"] < 0:
            raise ValueError("cost_price cannot be negative.")

        if not payload:
            return self.repo.get(purchase_id)

        return self.inventory.update_purchase_atomic(purchase_id, payload)

    def delete_purchase(self, purchase_id: int) -> bool:
        return self.inventory.delete_purchase_atomic(purchase_id)