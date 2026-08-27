"""
app/contracts/inventory_repository.py

Owns every operation that has to touch `purchases` and `stock`
atomically -- inserting, editing, or deleting a purchase all change
what stock *should* say, so all three go through here instead of
IPurchaseRepository. Everything read-only, or purely about purchases
metadata, stays on IPurchaseRepository.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.models import Purchase


class IInventoryRepository(ABC):

    @abstractmethod
    def record_inward_batch(self, items: List[dict]) -> List[Purchase]:
        """
        Inserts one purchase row per item AND applies the matching stock
        increase, in a single database transaction. Each item is
        self-contained: {"book_id", "qty", "cost_price", "purchase_date",
        "source_id", "recorded_by"}. Either every row lands (purchases +
        stock) or none of them do. Backs record_purchase (1 item),
        record_batch (N items), and record_inward_stock (N items).
        """
        ...

    @abstractmethod
    def update_purchase_atomic(self, purchase_id: int, fields: dict) -> Optional[Purchase]:
        """
        Updates a purchase row AND corrects stock by the resulting delta
        (handles a book_id change too), in one transaction. `fields` may
        contain any of: book_id, qty, cost_price, purchase_date,
        source_id, recorded_by.
        """
        ...

    @abstractmethod
    def delete_purchase_atomic(self, purchase_id: int) -> bool:
        """
        Deletes a purchase row AND reverses its contribution to stock,
        in one transaction.
        """
        ...