"""
Injected data-access boundary + all Languages business logic,
mirroring `app/domain/locations_domain.py`.
"""

from typing import List, Optional

from app.contracts.language_repository import ILanguageRepository
from app.injector import injector
from app.models import Language


@injector
class LanguagesDomain:
    """
    `repo` is auto-injected against the `ILanguageRepository` contract
    by `@injector` -- currently resolves to `SupabaseLanguageRepository`
    (see `app/container.py`).  Any object exposing the same interface
    can be passed in explicitly instead -- e.g. a fake for tests.
    """

    def __init__(self, repo: ILanguageRepository):
        self.repo = repo

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_languages(self) -> List[Language]:
        return self.repo.list_all()

    def get_language(self, language_id: int) -> Optional[Language]:
        return self.repo.get(language_id)

    def find_by_name(self, name: str) -> Optional[Language]:
        return self.repo.find_by_name(name)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def create_language(self, name: str) -> Language:
        name = (name or "").strip()
        if not name:
            raise ValueError("Language name is required.")
        if not self.repo.name_available(name):
            raise ValueError(f"Language '{name}' already exists.")
        return self.repo.add(Language(name=name))

    def rename_language(self, language_id: int, name: str) -> Optional[Language]:
        name = (name or "").strip()
        if not name:
            raise ValueError("Language name is required.")
        return self.repo.update(language_id, name=name)

    def delete_language(self, language_id: int) -> bool:
        return self.repo.delete(language_id)