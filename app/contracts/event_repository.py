"""
Storage contract for the Events domain, mirroring
`app/contracts/location_repository.py`.

Anything that wants to persist events (in-memory dict, SQLite,
Postgres, ...) implements this interface. The rest of the codebase
(`EventsDomain`, `MasterDataController`) only ever talks to this
contract, never to a concrete storage engine directly.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.models import Event


class IEventRepository(ABC):
    """Abstract contract for Event storage operations."""

    @abstractmethod
    def list_all(self) -> List[Event]:
        """Every event, ordered by name."""
        raise NotImplementedError

    @abstractmethod
    def get(self, event_id: int) -> Optional[Event]:
        """A single event by id, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Event]:
        """A single event by name, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def add(self, event: Event) -> Event:
        """Insert a new event. Caller is responsible for checking
        name_available() first -- this does not de-duplicate."""
        raise NotImplementedError

    @abstractmethod
    def update(self, event_id: int, **fields) -> Optional[Event]:
        """Patch one or more fields on an existing event. Returns the
        updated event, or None if the id doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, event_id: int) -> bool:
        """Remove an event. Returns whether a row was actually removed."""
        raise NotImplementedError

    @abstractmethod
    def name_available(self, name: str) -> bool:
        """True when no existing event already uses this name."""
        raise NotImplementedError