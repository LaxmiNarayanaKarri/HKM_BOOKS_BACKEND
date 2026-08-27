"""
Storage contract for the Categories domain, mirroring
`app/contracts/location_repository.py`.

Anything that wants to persist book categories (in-memory dict, SQLite,
Postgres, ...) implements this interface. The rest of the codebase
(`CategoriesDomain`, `MasterDataController`) only ever talks to this
contract, never to a concrete storage engine directly.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.models import Category


class ICategoryRepository(ABC):
    """Abstract contract for Category storage operations."""

    @abstractmethod
    def list_all(self) -> List[Category]:
        """Every category, ordered by name."""
        raise NotImplementedError

    @abstractmethod
    def get(self, category_id: int) -> Optional[Category]:
        """A single category by id, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Category]:
        """A single category by name, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def add(self, category: Category) -> Category:
        """Insert a new category. Caller is responsible for checking
        name_available() first -- this does not de-duplicate."""
        raise NotImplementedError

    @abstractmethod
    def update(self, category_id: int, **fields) -> Optional[Category]:
        """Patch one or more fields on an existing category. Returns the
        updated category, or None if the id doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, category_id: int) -> bool:
        """Remove a category. Returns whether a row was actually removed."""
        raise NotImplementedError

    @abstractmethod
    def name_available(self, name: str) -> bool:
        """True when no existing category already uses this name."""
        raise NotImplementedError