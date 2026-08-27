"""
Storage contract for the Locations domain, mirroring
`app/contracts/user_repository.py`.

Anything that wants to persist locations (in-memory dict, SQLite,
Postgres, ...) implements this interface. The rest of the codebase
(`LocationsDomain`, `LocationsController`) only ever talks to this
contract, never to a concrete storage engine directly.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.models import Location


class ILocationRepository(ABC):
    """Abstract contract for Location storage operations."""

    @abstractmethod
    def list_all(self) -> List[Location]:
        """Every location, ordered by name."""
        raise NotImplementedError

    @abstractmethod
    def get(self, location_id: int) -> Optional[Location]:
        """A single location by id, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Location]:
        """A single location by name, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def add(self, location: Location) -> Location:
        """Insert a new location. Caller is responsible for checking
        name_available() first -- this does not de-duplicate."""
        raise NotImplementedError

    @abstractmethod
    def update(self, location_id: int, **fields) -> Optional[Location]:
        """Patch one or more fields on an existing location. Returns the
        updated location, or None if the id doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, location_id: int) -> bool:
        """Remove a location. Returns whether a row was actually removed."""
        raise NotImplementedError

    @abstractmethod
    def name_available(self, name: str) -> bool:
        raise NotImplementedError