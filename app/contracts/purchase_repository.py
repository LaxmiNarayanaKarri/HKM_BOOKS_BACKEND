"""
Storage contract for the Purchases domain, mirroring
`app/contracts/location_repository.py`.

Anything that wants to persist Purchases (in-memory dict, SQLite,
Postgres, ...) implements this interface. The rest of the codebase
(`PurchasesDomain`, `BooksController`) only ever talks to this
contract, never to a concrete storage engine directly.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from app.models import Purchase


class IPurchaseRepository(ABC):
    """Abstract contract for Purchase storage operations."""

    @abstractmethod
    def list_all(self) -> List[Purchase]:
        """Every Purchase, most recent purchase_date first."""
        raise NotImplementedError

    @abstractmethod
    def get(self, purchase_id: int) -> Optional[Purchase]:
        """A single Purchase by id, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Purchase]:
        """A single Purchase matched against `short_title`, or None.
        Not de-duplicating (purchases legitimately repeat) — mainly
        useful for quick lookups/autocomplete against past entries."""
        raise NotImplementedError

    @abstractmethod
    def add(self, purchase: Purchase) -> Purchase:
        """Insert a new Purchase row."""
        raise NotImplementedError

    @abstractmethod
    def add_batch(self, purchases: List[Purchase]) -> List[Purchase]:
        """Insert several Purchase rows in one round trip. Returns the
        rows actually inserted (with ids populated)."""
        raise NotImplementedError

    @abstractmethod
    def update(self, purchase_id: int, **fields) -> Optional[Purchase]:
        """Patch one or more fields on an existing Purchase. Returns the
        updated Purchase, or None if the id doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, purchase_id: int) -> bool:
        """Remove a Purchase. Returns whether a row was actually removed."""
        raise NotImplementedError

    @abstractmethod
    def name_available(self, name: str) -> bool:
        """Kept for interface parity with other repos; purchases don't
        de-duplicate on short_title, so this only checks whether that
        short_title has been used before (informational, not a guard)."""
        raise NotImplementedError

    @abstractmethod
    def list_filtered(
        self,
        *,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Purchase]:
        """Recent-purchases feed for the inward-stock page/export —
        filtered by purchase_date range and a free-text match against
        short_title, most recent first."""
        raise NotImplementedError