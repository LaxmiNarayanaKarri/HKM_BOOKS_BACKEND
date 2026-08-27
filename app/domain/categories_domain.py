"""
Injected data-access boundary + all Book Categories business logic,
mirroring `app/domain/locations_domain.py`.
"""

from typing import List, Optional

from app.contracts.category_repository import ICategoryRepository
from app.injector import injector
from app.models import Category


@injector
class CategoriesDomain:
    """
    `repo` is auto-injected against the `ICategoryRepository` contract
    by `@injector` -- currently resolves to `SupabaseCategoryRepository`
    (see `app/container.py`).  Any object exposing the same interface
    can be passed in explicitly instead -- e.g. a fake for tests.
    """

    def __init__(self, repo: ICategoryRepository):
        self.repo = repo

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_categories(self) -> List[Category]:
        return self.repo.list_all()

    def get_category(self, category_id: int) -> Optional[Category]:
        return self.repo.get(category_id)

    def find_by_name(self, name: str) -> Optional[Category]:
        return self.repo.find_by_name(name)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def create_category(self, name: str) -> Category:
        name = (name or "").strip()
        if not name:
            raise ValueError("Category name is required.")
        if not self.repo.name_available(name):
            raise ValueError(f"Category '{name}' already exists.")
        return self.repo.add(Category(name=name))

    def rename_category(self, category_id: int, name: str) -> Optional[Category]:
        name = (name or "").strip()
        if not name:
            raise ValueError("Category name is required.")
        return self.repo.update(category_id, name=name)

    def delete_category(self, category_id: int) -> bool:
        return self.repo.delete(category_id)