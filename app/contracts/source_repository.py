"""
Storage contract for the Sources domain, mirroring
`app/contracts/location_repository.py`.

Anything that wants to persist book sources (in-memory dict, SQLite,
Postgres, ...) implements this interface. The rest of the codebase
(`Sources Domain`, `MasterDataController`) only ever talks to this
contract, never to a concrete storage engine directly.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.models import Category, Source


class ISourceRepository(ABC):
    """Abstract contract for Source storage operations."""

    @abstractmethod
    def list_all(self) -> List[Source]:
        """Every source, ordered by name."""
        raise NotImplementedError

    @abstractmethod
    def get(self, source_id: int) -> Optional[Source]:
        """A single source by id, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Source]:
        """A single source by name, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def add(self, source: Source) -> Source:
        """Insert a new source. Caller is responsible for checking
        name_available() first -- this does not de-duplicate."""
        raise NotImplementedError

    @abstractmethod
    def update(self, source_id: int, **fields) -> Optional[Source]:
        """Patch one or more fields on an existing source. Returns the
        updated source, or None if the id doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, source_id: int) -> bool:
        """Remove a source. Returns whether a row was actually removed."""
        raise NotImplementedError

    @abstractmethod
    def name_available(self, name: str) -> bool:
        """True when no existing source already uses this name."""
        raise NotImplementedError