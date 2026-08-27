"""
app/contracts/stock_repository.py

Storage-agnostic contract for the `stock` table. Concrete implementations
(e.g. SupabaseStockRepository) live in app/repositories and are wired up
in app/container.py -- StockDomain never references them directly.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.models import Stock, StockDelta


class IStockRepository(ABC):

    @abstractmethod
    def list_all(self) -> List[Stock]:
        ...

    @abstractmethod
    def get(self, stock_id: int) -> Optional[Stock]:
        ...

    @abstractmethod
    def get_by_book_id(self, book_id: int) -> Optional[Stock]:
        ...

    @abstractmethod
    def add(self, stock: Stock) -> Stock:
        ...

    @abstractmethod
    def update(self, stock_id: int, **fields) -> Optional[Stock]:
        ...

    @abstractmethod
    def delete(self, stock_id: int) -> bool:
        ...

    @abstractmethod
    def upsert_batch(self, deltas: List["StockDelta"]) -> List[Stock]:
        """
        Applies a signed quantity delta per book_id in one round trip.
        Creates the stock row if it doesn't exist yet (delta must be
        positive in that case). Implementations should apply all deltas
        atomically with respect to each other -- see SupabaseStockRepository,
        which does this via a single Postgres function.

        NOTE: this only guarantees atomicity *within the stock table*.
        It does NOT make a caller that also writes to another table (e.g.
        purchases) atomic -- for that, see IInventoryRepository.
        """
        ...


