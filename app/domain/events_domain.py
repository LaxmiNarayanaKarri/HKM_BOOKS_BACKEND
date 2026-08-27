"""
Injected data-access boundary + all Events business logic,
mirroring `app/domain/locations_domain.py`.
"""

from typing import List, Optional

from app.contracts.event_repository import IEventRepository
from app.injector import injector
from app.models import Event


@injector
class EventsDomain:
    """
    `repo` is auto-injected against the `IEventRepository` contract
    by `@injector` -- currently resolves to `SupabaseEventRepository`
    (see `app/container.py`).  Any object exposing the same interface
    can be passed in explicitly instead -- e.g. a fake for tests.
    """

    def __init__(self, repo: IEventRepository):
        self.repo = repo

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_events(self) -> List[Event]:
        return self.repo.list_all()

    def get_event(self, event_id: int) -> Optional[Event]:
        return self.repo.get(event_id)

    def find_by_name(self, name: str) -> Optional[Event]:
        return self.repo.find_by_name(name)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def create_event(self, name: str) -> Event:
        name = (name or "").strip()
        if not name:
            raise ValueError("Event name is required.")
        if not self.repo.name_available(name):
            raise ValueError(f"Event '{name}' already exists.")
        return self.repo.add(Event(name=name))

    def rename_event(self, event_id: int, name: str) -> Optional[Event]:
        name = (name or "").strip()
        if not name:
            raise ValueError("Event name is required.")
        return self.repo.update(event_id, name=name)

    def delete_event(self, event_id: int) -> bool:
        return self.repo.delete(event_id)