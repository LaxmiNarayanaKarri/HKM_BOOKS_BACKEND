"""
Injected data-access boundary + all Locations business logic, mirroring
`app/domain/users_domain.py`.
"""

from typing import List, Optional

from app.contracts.location_repository import ILocationRepository
from app.injector import injector
from app.models import Location


@injector
class LocationsDomain:
    """
    `repo` is auto-injected against the `ILocationRepository` contract
    by `@injector` -- currently that resolves to
    `SupabaseLocationRepository` (see `app/container.py`), but this
    class never references that (or any other concrete storage engine)
    directly. Any object exposing the same interface can be passed in
    explicitly instead -- e.g. a fake for tests.
    """

    def __init__(self, repo: ILocationRepository):
        self.repo = repo

    def list_locations(self) -> List[Location]:
        return self.repo.list_all()

    def get_location(self, location_id: int) -> Optional[Location]:
        return self.repo.get(location_id)

    def find_by_name(self, name: str) -> Optional[Location]:
        return self.repo.find_by_name(name)

    def create_location(self, name: str) -> Location:
        name = (name or "").strip()
        if not name:
            raise ValueError("Location name is required.")
        if not self.repo.name_available(name):
            raise ValueError(f"Location '{name}' already exists.")
        return self.repo.add(Location(name=name))

    def rename_location(self, location_id: int, name: str) -> Optional[Location]:
        name = (name or "").strip()
        if not name:
            raise ValueError("Location name is required.")
        return self.repo.update(location_id, name=name)

    def delete_location(self, location_id: int) -> bool:
        return self.repo.delete(location_id)

    def get_all_locations(self) -> List[Location]:
        """
        Returns a list of all distribution locations.
        """
        return self.repo.list_all()