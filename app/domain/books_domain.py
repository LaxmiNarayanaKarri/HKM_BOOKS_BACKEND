"""
Injected data-access boundary + all Catalog (Books) business logic,
mirroring `app/domain/locations_domain.py`.
"""

from typing import List, Optional

from app.contracts.book_repository import IBookRepository
from app.injector import injector
from app.models import Book

class ValidationError(Exception):
    """Input failed a business rule (bad password length, duplicate
    username, missing field, ...)."""


@injector
class BooksDomain:
    """
    `repo` is auto-injected against the `IBookRepository` contract
    by `@injector` -- currently that resolves to
    `SupabaseBookRepository` (see `app/container.py`), but this class
    never references that (or any other concrete storage engine)
    directly. Any object exposing the same interface can be passed in
    explicitly instead -- e.g. a fake for tests.
    """

    def __init__(self, repo: IBookRepository):
        self.repo = repo

    def list_books(self) -> List[Book]:
        return self.repo.list_all()

    def get_book(self, book_id: int) -> Optional[Book]:
        return self.repo.get(book_id)

    def find_by_title(self, title: str) -> Optional[Book]:
        return self.repo.find_by_title(title)

    def create_book(
        self,
        title: str,
        threshold: int,
        short_title: Optional[str] = None,
        category: Optional[int] = None,
        language: Optional[int] = None,
        opening_stock: Optional[int] = None,
    ) -> Book:
        title = (title or "").strip()
        if not title:
            raise ValueError("Book title is required.")
        if not self.repo.title_available(title):
            raise ValueError(f"Book '{title}' already exists.")
        return self.repo.add(
            Book(
                title=title,
                short_title=short_title,
                category_id=category,
                threshold=threshold,
                opening_stock=opening_stock,
                language_id=language
            )
        )

    def update_book(self, book_id: int, **fields) -> Optional[Book]:
        if "title" in fields:
            fields["title"] = (fields["title"] or "").strip()
            if not fields["title"]:
                raise ValueError("Book title is required.")
        return self.repo.update(book_id, **fields)

    def delete_book(self, book_id: int) -> bool:
        return self.repo.delete(book_id)

    def master_data_add_book(self, payload) -> tuple[Book, bool]:
        """
        Add a book to the catalog if it doesn't already exist.
        Returns a tuple of (Book, bool) where the bool indicates whether
        the book was newly created (True) or already existed (False).
        """
        title = (payload.get("title") or "").strip()
        if not title:
            raise ValueError("Book title is required.")
        
        existing_book = self.repo.find_by_title(title)
        if existing_book:
            return existing_book, False  # Book already exists
        
        new_book = self.repo.add(
            Book(
                title=title,
                short_title=payload.get("short_title"),
                category=payload.get("category"),
                language=payload.get("language"),
                threshold=payload.get("threshold", 0),
                opening_stock=payload.get("opening_stock", 0),
            )
        )
        return new_book, True  # New book created

    def find_by_title(self, title: str) -> Optional[Book]:
        return self.repo.find_by_title(title)
 
    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
 
    def update_threshold(self, title: str, threshold: int) -> Optional[Book]:
        if threshold < 0:
            raise ValueError("Threshold must be 0 or greater.")
        book = self.find_by_title(title)
        if not book:
            raise ValueError(f"Book '{title}' not found.")
        return self.repo.update(book.id, threshold=threshold)
 
    def rename_book(
        self,
        book_id: int,
        title: str,
        short_title: Optional[str] = None,
    ) -> Optional[Book]:
        title = (title or "").strip()
        if not title:
            raise ValueError("Book title is required.")
 
        short_title = (short_title or "").strip() or None
        if short_title and len(short_title) > 40:
            raise ValueError("Short title must be 40 characters or fewer.")
 
        return self.repo.update(book_id, title=title, short_title=short_title)
