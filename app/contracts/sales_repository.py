"""
Storage contract for aggregate Sales figures -- the "Locations
Overview" panel on the Users service's volunteer-assignment page
(consumed over HTTP via app/api/routers/internal.py).

Kept separate from ISellEntryRepository (app/contracts/sell_entry_repository.py),
which is the raw per-sale-row contract behind the "Books & Sell Entry"
page -- listing/filtering "My Recent Entries", inserting a new sale,
and producing export rows. This contract is only ever about totals.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class ISalesRepository(ABC):
    """Abstract contract for aggregate Sales-figure storage operations."""

    @abstractmethod
    def get_sales_overview(
        self,
        ov_date_from: str,
        ov_date: str,
        ov_location: str,
        ov_event: str,
    ) -> Dict[str, Any]:
        """
        Aggregate sales revenue (qty * sell_price) for the given
        date/location/event filters, grouped by location.

        Filter semantics:
            ov_date_from + ov_date together -> inclusive range bound
                (sales_date between ov_date_from and ov_date);
            ov_date_from alone -> open-ended lower bound;
            ov_date alone -> exact match on that single date;
            neither -> no date filter.
            ov_location/ov_event == "all" (or blank) -> no filter on
                that column; otherwise resolved from name to id and
                filtered. A name that doesn't resolve to any known
                location/event returns an empty result rather than
                silently ignoring the filter.

        Expected return shape:
            {
                "sales_by_location": {location_name: revenue_total, ...},
                "total_sales": <float>,
            }
        """
        raise NotImplementedError
