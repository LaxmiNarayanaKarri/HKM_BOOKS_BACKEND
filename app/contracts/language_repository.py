"""
Storage contract for the Languages domain, mirroring
`app/contracts/location_repository.py`.

Anything that wants to persist languages (in-memory dict, SQLite,
Postgres, ...) implements this interface. The rest of the codebase
(`LanguagesDomain`, `MasterDataController`) only ever talks to this
contract, never to a concrete storage engine directly.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.models import Language


class ILanguageRepository(ABC):
    """Abstract contract for Language storage operations."""

    @abstractmethod
    def list_all(self) -> List[Language]:
        """Every language, ordered by name."""
        raise NotImplementedError

    @abstractmethod
    def get(self, language_id: int) -> Optional[Language]:
        """A single language by id, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Language]:
        """A single language by name, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def add(self, language: Language) -> Language:
        """Insert a new language. Caller is responsible for checking
        name_available() first -- this does not de-duplicate."""
        raise NotImplementedError

    @abstractmethod
    def update(self, language_id: int, **fields) -> Optional[Language]:
        """Patch one or more fields on an existing language. Returns the
        updated language, or None if the id doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, language_id: int) -> bool:
        """Remove a language. Returns whether a row was actually removed."""
        raise NotImplementedError

    @abstractmethod
    def name_available(self, name: str) -> bool:
        """True when no existing language already uses this name."""
        raise NotImplementedError