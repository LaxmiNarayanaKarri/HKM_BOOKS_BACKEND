"""
Controller for Sales. Thin layer over SalesDomain — owns input
normalization and response shaping for the HTTP boundary, but no
business logic of its own (that lives in SalesDomain) and no
knowledge of volunteers/assignments (that's the Users side's job;
see UsersController, which merges this output with volunteer data).
"""
from typing import List, Optional

from app.domain.sales_domain import SalesDomain
from app.domain.sell_domain import SellDomain
from app.models import SaleCreate, SaleRow


class SalesController:
    """
    Composes two independent domains, mirroring how
    `PurchasesController` composes `PurchasesDomain` with its
    reference-data domains:

    - `sales` (`SalesDomain`) -- aggregate totals for the "Locations
      Overview" panel (see `get_location_overview`, called by the
      Users service over HTTP via `app/api/routers/internal.py`).
    - `sell` (`SellDomain`) -- the per-sale-row "Books & Sell Entry"
      workflow (page data, recording a sale, exports).

    Each domain is `@injector`-decorated itself and resolves its own
    repository from the DI container, so `SalesController` never talks
    to storage directly and has no knowledge of volunteers/assignments
    (that's the Users side's job; see UsersController, which merges
    this output with volunteer data).
    """

    def __init__(
        self,
        sales: Optional[SalesDomain] = None,
        sell: Optional[SellDomain] = None,
    ):
        self.sales = sales if sales is not None else SalesDomain()
        self.sell = sell if sell is not None else SellDomain()

    # ------------------------------------------------------------------
    # Locations Overview (sales-only)
    # ------------------------------------------------------------------

    def get_location_overview(
        self,
        ov_date_from: str = "",
        ov_date: str = "",
        ov_location: str = "all",
        ov_event: str = "all",
    ) -> dict:
        """
        Sales totals for the given date range / date / location /
        event filters. Does NOT include volunteer counts — that's
        computed separately from VolunteerDomain and merged by the
        caller (UsersController.volunteer_assignment_page_data).
        """
        ov_date_from = (ov_date_from or "").strip()
        ov_date = (ov_date or "").strip()
        ov_location = (ov_location or "all").strip() or "all"
        ov_event = (ov_event or "all").strip() or "all"

        result = self.sales.get_sales_overview(
            ov_date_from, ov_date, ov_location, ov_event
        )

        return {
            "ov_date_from": ov_date_from,
            "ov_date": ov_date,
            "ov_location": ov_location,
            "ov_event": ov_event,
            "sales_by_location": result.get("sales_by_location", {}),
            "sales_by_location_volunteer": result.get("sales_by_location_volunteer", {}),
            "total_sales": result.get("total_sales", 0),
        }

    def sell_entry_page_data(
        self,
        username: str,
        se_user: str = "all",
        se_event: str = "all",
        se_date_from: str = "",
        se_date_to: str = "",
        se_location: str = ""
    ) -> dict:
        return self.sell.sell_entry_page_data(
            username, se_user, se_event, se_date_from, se_date_to, se_location
        )
 
    def record_sell_entry(self, username: str, payload: SaleCreate) -> SaleRow:
        return self.sell.record_sell_entry(username, payload)
 
    def export_sell_entries_rows(
        self,
        username: str,
        se_user: str = "all",
        se_event: str = "all",
        se_date_from: str = "",
        se_date_to: str = "",
    ) -> List[dict]:
        return self.sell.export_sell_entries_rows(
            username, se_user, se_event, se_date_from, se_date_to
        )

    # ------------------------------------------------------------------
    # Room to grow: other sales-only endpoints (e.g. per-book sales,
    # sales history, exports) belong here rather than on BooksController.
    # ------------------------------------------------------------------