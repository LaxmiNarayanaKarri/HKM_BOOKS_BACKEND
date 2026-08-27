"""
app/domain/stock_domain.py

Injected data-access boundary + all Stock business logic, mirroring
`app/domain/locations_domain.py` / `app/domain/users_domain.py`.
"""

from typing import Dict, List, Optional

from app.contracts.stock_repository import IStockRepository, StockDelta
from app.injector import injector
from app.models import Stock


@injector
class StockDomain:
    """
    `repo` is auto-injected against the `IStockRepository` contract by
    `@injector` -- resolves to a concrete repository (see app/container.py),
    but this class never references any storage engine directly. Any
    object exposing the same interface can be passed in explicitly
    instead -- e.g. a fake for tests.
    """

    def __init__(self, repo: IStockRepository):
        self.repo = repo

    def list_stock(self) -> List[Stock]:
        return self.repo.list_all()

    def get_stock(self, stock_id: int) -> Optional[Stock]:
        return self.repo.get(stock_id)

    def get_stock_by_book(self, book_id: int) -> Optional[Stock]:
        return self.repo.get_by_book_id(book_id)

    def create_stock(self, book_id: int, stock: int = 0, cost: Optional[int] = None) -> Stock:
        """
        Creates the stock row for a book. One row per book_id -- if a row
        already exists, use adjust_stock / update_cost instead of creating
        a second one.
        """
        if book_id is None:
            raise ValueError("book_id is required.")
        if stock < 0:
            raise ValueError("Initial stock cannot be negative.")
        if cost is not None and cost < 0:
            raise ValueError("Cost cannot be negative.")

        if self.repo.get_by_book_id(book_id) is not None:
            raise ValueError(f"Stock already exists for book_id {book_id}.")

        return self.repo.add(Stock(book_id=book_id, stock=stock, cost=cost))

    def adjust_stock(self, book_id: int, delta: int) -> Stock:
        """
        Applies a signed quantity change to a book's stock -- positive for
        inward stock, negative for sales/deductions. Raises if there's no
        stock row for the book yet, or if the result would go negative.
        """
        current = self.repo.get_by_book_id(book_id)
        if current is None:
            raise ValueError(f"No stock row exists for book_id {book_id}.")

        new_quantity = (current.stock or 0) + delta
        if new_quantity < 0:
            raise ValueError(
                f"Cannot reduce stock for book_id {book_id} by {abs(delta)}; "
                f"only {current.stock} on hand."
            )

        return self.repo.update(current.id, stock=new_quantity)

    def adjust_stock_for_batch(self, items: List[dict]) -> List[Stock]:
        """
        Applies inward/outward quantity deltas for a batch of items in
        one round trip. `items` is [{"book_id": int, "qty": int}, ...];
        multiple entries for the same book_id are summed before writing,
        so each book's stock row is only touched once.

        IMPORTANT: this only guarantees atomicity across the stock rows
        in this batch -- it says nothing about any other table. If this
        batch is one half of a larger operation (e.g. also inserting
        purchase rows), do NOT call this from that flow -- use
        IInventoryRepository.record_inward_batch instead, which commits
        both tables in a single DB transaction.
        """
        if not items:
            return []

        deltas: Dict[int, int] = {}
        for item in items:
            book_id = item.get("book_id")
            qty = item.get("qty")
            if book_id is None:
                raise ValueError("Item missing book_id.")
            if qty is None or qty == 0:
                raise ValueError(f"qty must be non-zero for book_id {book_id}.")
            deltas[book_id] = deltas.get(book_id, 0) + qty

        return self.repo.upsert_batch(
            [StockDelta(book_id=b, delta=d) for b, d in deltas.items()]
        )

    def update_cost(self, book_id: int, cost: int) -> Stock:
        if cost < 0:
            raise ValueError("Cost cannot be negative.")

        current = self.repo.get_by_book_id(book_id)
        if current is None:
            raise ValueError(f"No stock row exists for book_id {book_id}.")

        return self.repo.update(current.id, cost=cost)

    def delete_stock(self, stock_id: int) -> bool:
        return self.repo.delete(stock_id)

    def get_all_stock(self) -> List[Stock]:
        """
        Returns a list of all stock records.
        """
        return self.repo.list_all()