"""
Injected data-access boundary + all Sources business logic,
mirroring `app/domain/locations_domain.py`.
"""

from typing import List, Optional

from app.contracts.source_repository import ISourceRepository
from app.injector import injector
from app.models import Event


@injector
class SourcesDomain:
    """
    `repo` is auto-injected against the `ISourceRepository` contract
    by `@injector` -- currently resolves to `SupabaseSourceRepository`
    (see `app/container.py`).  Any object exposing the same interface
    can be passed in explicitly instead -- e.g. a fake for tests.
    """

    def __init__(self, repo: ISourceRepository):
        self.repo = repo

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_sources(self) -> List[Event]:
        return self.repo.list_all()

    def get_source(self, source_id: int) -> Optional[Event]:
        return self.repo.get(source_id)

    def find_by_name(self, name: str) -> Optional[Event]:
        return self.repo.find_by_name(name)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def create_source(self, name: str) -> Event:
        name = (name or "").strip()
        if not name:
            raise ValueError("Source name is required.")
        if not self.repo.name_available(name):
            raise ValueError(f"Source '{name}' already exists.")
        return self.repo.add(Event(name=name))

    def rename_source(self, source_id: int, name: str) -> Optional[Event]:
        name = (name or "").strip()
        if not name:
            raise ValueError("Source name is required.")
        return self.repo.update(source_id, name=name)

    def delete_source(self, source_id: int) -> bool:
        return self.repo.delete(source_id)