"""
Concrete storage for aggregate Sales figures (the "Locations Overview"
panel on the volunteer-assignment page), backed by Supabase.

Queries the real `sales` table directly:

    sales
    -----
    id                bigint  primary key
    sales_date        date    not null
    book_id           bigint  null
    category_id       bigint  null
    seller_username   varchar null
    qty               bigint  null
    cost_price        double  null
    sell_price        double  null
    language_id       bigint  null
    location_id       bigint  null
    event_id          bigint  null
    created_at        timestamptz null

`ov_location` / `ov_event` arrive as human-readable names (from the
filter dropdowns), so this repo resolves them to location_id/event_id
via ILocationRepository/IEventRepository before querying -- it never
guesses at name columns that don't exist on `sales`.
"""
from typing import Optional

from app.contracts.event_repository import IEventRepository
from app.contracts.location_repository import ILocationRepository
from app.contracts.sales_repository import ISalesRepository
from app.injector import DBContract, injector, singleton

TABLE = "sales"


@singleton(ISalesRepository)
@injector
class SupabaseSalesRepository(ISalesRepository):
    """`db`, `location_repo`, and `event_repo` are all auto-injected by
    `@injector` against their respective contracts."""

    def __init__(
        self,
        db: DBContract,
        location_repo: ILocationRepository,
        event_repo: IEventRepository,
    ):
        self.db = db
        self.location_repo = location_repo
        self.event_repo = event_repo

    # -- internal helpers -------------------------------------------------
    @property
    def _table(self):
        return self.db.get_client().table(TABLE)

    def _resolve_location_id(self, ov_location: str) -> Optional[int]:
        """
        ASSUMPTION: ILocationRepository exposes find_by_name(name) ->
        Optional[object with .id]. Adjust if your actual contract uses
        a different method name.
        """
        if not ov_location or ov_location == "all":
            return None
        loc = self.location_repo.find_by_name(ov_location)
        return loc.id if loc else None

    def _resolve_event_id(self, ov_event: str) -> Optional[int]:
        """ASSUMPTION: IEventRepository exposes find_by_name(name) ->
        Optional[object with .id], mirroring the location repo."""
        if not ov_event or ov_event == "all":
            return None
        evt = self.event_repo.find_by_name(ov_event)
        return evt.id if evt else None

    def _location_name_by_id(self, location_id: Optional[int]) -> str:
        if location_id is None:
            return ""
        loc = self.location_repo.get(location_id)
        return loc.name if loc else ""

    # -- ISalesRepository ---------------------------------------------------
    def get_sales_overview(
        self,
        ov_date_from: str,
        ov_date: str,
        ov_location: str,
        ov_event: str,
    ) -> dict:
        query = self._table.select("location_id, event_id, qty, sell_price")

        if ov_date_from and ov_date:
            query = query.gte("sales_date", ov_date_from).lte("sales_date", ov_date)
        elif ov_date_from:
            query = query.gte("sales_date", ov_date_from)
        elif ov_date:
            query = query.eq("sales_date", ov_date)

        location_id = self._resolve_location_id(ov_location)
        if location_id is not None:
            query = query.eq("location_id", location_id)
        elif ov_location and ov_location != "all":
            # A location name was given but didn't resolve to any row --
            # return an empty result rather than silently ignoring the filter.
            return {"sales_by_location": {}, "total_sales": 0}

        event_id = self._resolve_event_id(ov_event)
        if event_id is not None:
            query = query.eq("event_id", event_id)
        elif ov_event and ov_event != "all":
            return {"sales_by_location": {}, "total_sales": 0}

        res = query.execute()
        rows = res.data or []

        # Sum row totals (qty * sell_price) grouped by location_id, then
        # resolve ids -> names once at the end (fewer repo round-trips
        # than resolving per-row).
        totals_by_location_id: dict[Optional[int], float] = {}
        total_sales = 0.0
        for row in rows:
            loc_id = row.get("location_id")
            qty = row.get("qty") or 0
            sell_price = row.get("sell_price") or 0
            row_total = qty * sell_price
            totals_by_location_id[loc_id] = totals_by_location_id.get(loc_id, 0) + row_total
            total_sales += row_total

        sales_by_location: dict[str, float] = {}
        for loc_id, amount in totals_by_location_id.items():
            name = self._location_name_by_id(loc_id) or "(Unknown Location)"
            sales_by_location[name] = sales_by_location.get(name, 0) + amount

        return {
            "sales_by_location": sales_by_location,
            "total_sales": total_sales,
        }