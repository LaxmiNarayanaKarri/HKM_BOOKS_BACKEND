"""
Storage contract for Sell Entries -- individual sale rows recorded on
the "Books & Sell Entry" page. Kept separate from ISalesRepository
(which is aggregate totals for the volunteer-assignment Locations
Overview panel) -- this contract is about the raw per-sale records
themselves: listing/filtering "My Recent Entries", inserting a new
sale, and producing export rows.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.models import SaleCreate, SaleRow


class ISellEntryRepository(ABC):
    """Abstract contract for Sell-Entry storage operations."""

    @abstractmethod
    def get_page_data(
        self,
        username: str,
        se_user: str,
        se_event: str,
        se_date_from: str,
        se_date_to: str,
        se_location: str
    ) -> Dict[str, Any]:
        """
        Everything the Sell Entry page needs in one call: locations,
        book_titles, book_stock, users (for the filter dropdown), and
        my_sales -- the latter filtered by se_user/se_event/date range.

        Filter semantics mirror ISalesRepository.get_sales_overview:
        se_user/se_event == "all" -> no filter on that column;
        se_date_from + se_date_to together -> inclusive range;
        either alone -> open-ended bound; neither -> no date filter.

        Expected return shape:
            {
                "locations": [...],
                "book_titles": [...],
                "book_stock": {title: qty, ...},
                "users": [...],
                "my_sales": [
                    {"date": ..., "title": ..., "location": ...,
                     "qty": ..., "sell_price": ..., "seller": ...,
                     "recorded_by_name": ...},
                    ...
                ],
            }
        """
        raise NotImplementedError

    @abstractmethod
    def add_sale(self, username: str, payload: SaleCreate) -> SaleRow:
        """Insert a new sale (one or more book-line items) recorded by
        `username`. Returns the created row (or the last row, if the
        payload contains multiple items and the caller only needs one
        for the confirmation message)."""
        raise NotImplementedError

    @abstractmethod
    def list_export_rows(
        self,
        username: str,
        se_user: str,
        se_event: str,
        se_date_from: str,
        se_date_to: str,
    ) -> List[Dict[str, Any]]:
        """Same filter semantics as get_page_data's my_sales, but
        returned as plain dicts shaped for xlsx export (date, title,
        location, qty, sell_price)."""
        raise NotImplementedError

    @abstractmethod
    def list_sales_rows(
        self,
        se_user: str = "all",
        se_event: str = "all",
        se_date_from: str = "",
        se_date_to: str = "",
        se_location: str = "all",
        limit: Optional[int] = None,
    ) -> List[Any]:
        """Full `SaleRow` objects (title/cost_price/sell_price/qty/
        seller_username included) for the given filters, with no row
        cap unless `limit` is given. Backs dashboard aggregation
        (KPIs, leaderboard, top books) -- unlike `get_page_data`'s
        `my_sales`, which is capped for the "My Recent Entries" feed
        and only carries display fields, not cost_price."""
        raise NotImplementedError

    @abstractmethod
    def list_sellers(self) -> List[str]:
        """Every distinct seller_username that has ever recorded a
        sale, sorted alphabetically -- backs the seller filter
        dropdown on the dashboard."""
        raise NotImplementedError