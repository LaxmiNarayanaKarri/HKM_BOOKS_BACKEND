"""
Storage contract for the Catalog (Books) domain, mirroring
`app/contracts/location_repository.py`.

Anything that wants to persist books (in-memory dict, SQLite,
Postgres, ...) implements this interface. The rest of the codebase
(`BooksDomain`, `BooksController`) only ever talks to this contract,
never to a concrete storage engine directly.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.models import Book


class IBookRepository(ABC):
    """Abstract contract for Book storage operations."""

    @abstractmethod
    def list_all(self) -> List[Book]:
        """Every book, ordered by title."""
        raise NotImplementedError

    @abstractmethod
    def get(self, book_id: int) -> Optional[Book]:
        """A single book by id, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def find_by_title(self, title: str) -> Optional[Book]:
        """A single book by title, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, id: str) -> Optional[Book]:
        """A single book by id, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def add(self, book: Book) -> Book:
        """Insert a new book. Caller is responsible for checking
        title_available() first -- this does not de-duplicate."""
        raise NotImplementedError

    @abstractmethod
    def update(self, book_id: int, **fields) -> Optional[Book]:
        """Patch one or more fields on an existing book. Returns the
        updated book, or None if the id doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, book_id: int) -> bool:
        """Remove a book. Returns whether a row was actually removed."""
        raise NotImplementedError

    @abstractmethod
    def title_available(self, title: str) -> bool:
        raise NotImplementedError