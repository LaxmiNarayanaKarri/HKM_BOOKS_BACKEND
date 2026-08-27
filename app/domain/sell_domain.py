"""
Business logic for Sell Entries. Mirrors the shape of SalesDomain but
operates on individual sale rows rather than aggregate totals.
"""
from typing import Any, Dict, List

from app.contracts.sell_entry_repository import ISellEntryRepository
from app.core.errors import ValidationError
from app.injector import injector
from app.models import SaleCreate, SaleRow


@injector
class SellDomain:
    def __init__(self, repo: ISellEntryRepository):
        self.repo = repo

    @staticmethod
    def _normalize_filters(
        se_user: str, se_event: str, se_date_from: str, se_date_to: str, se_location: str
    ) -> tuple[str, str, str, str, str]:
        se_user = (se_user or "all").strip() or "all"
        se_event = (se_event or "all").strip() or "all"
        se_date_from = (se_date_from or "").strip()
        se_date_to = (se_date_to or "").strip()
        se_location = (se_location or "all").strip() or "all"
        return se_user, se_event, se_date_from, se_date_to, se_location

    def sell_entry_page_data(
        self,
        username: str,
        se_user: str = "all",
        se_event: str = "all",
        se_date_from: str = "",
        se_date_to: str = "",
        se_location: str = ""
    ) -> Dict[str, Any]:
        se_user, se_event, se_date_from, se_date_to, se_location = self._normalize_filters(
            se_user, se_event, se_date_from, se_date_to, se_location
        )
        return self.repo.get_page_data(
            username, se_user, se_event, se_date_from, se_date_to, se_location
        )

    def record_sell_entry(self, username: str, payload: SaleCreate) -> SaleRow:
        if not payload.items:
            raise ValidationError("At least one book row is required.")
        for item in payload.items:
            if item.qty is not None and item.qty < 0:
                raise ValidationError(f"Quantity for '{item.title}' cannot be negative.")
            if item.sell_price is not None and item.sell_price < 0:
                raise ValidationError(f"Sell price for '{item.title}' cannot be negative.")
        return self.repo.add_sale(username, payload)

    def export_sell_entries_rows(
        self,
        username: str,
        se_user: str = "all",
        se_event: str = "all",
        se_date_from: str = "",
        se_date_to: str = "",
    ) -> List[Dict[str, Any]]:
        se_user, se_event, se_date_from, se_date_to = self._normalize_filters(
            se_user, se_event, se_date_from, se_date_to
        )
        return self.repo.list_export_rows(
            username, se_user, se_event, se_date_from, se_date_to
        )