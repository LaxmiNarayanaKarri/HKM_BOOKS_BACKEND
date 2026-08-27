"""
Injected data-access boundary + aggregate Sales business logic,
mirroring `app/domain/locations_domain.py`. Backs the "Locations
Overview" panel on the Users service's volunteer-assignment page
(see `app/api/routers/internal.py` -> `SalesController.get_location_overview`).

Kept separate from `SellDomain` (`app/domain/sell_domain.py`), which
owns the per-sale-row "Books & Sell Entry" workflow -- this class only
ever deals in aggregate totals.
"""

from typing import Any, Dict

from app.contracts.sales_repository import ISalesRepository
from app.injector import injector


@injector
class SalesDomain:
    """
    `repo` is auto-injected against the `ISalesRepository` contract by
    `@injector` -- currently that resolves to `SupabaseSalesRepository`
    (see `app/container.py`), but this class never references that (or
    any other concrete storage engine) directly. Any object exposing
    the same interface can be passed in explicitly instead -- e.g. a
    fake for tests.
    """

    def __init__(self, repo: ISalesRepository):
        self.repo = repo

    def get_sales_overview(
        self,
        ov_date_from: str,
        ov_date: str,
        ov_location: str,
        ov_event: str,
    ) -> Dict[str, Any]:
        return self.repo.get_sales_overview(ov_date_from, ov_date, ov_location, ov_event)
