"""
Controller for the Catalog (Books) domain -- same role as
`app/controllers/locations_controller.py`: routers hand this plain,
already-parsed values and get back plain data or a domain exception.
"""

from typing import Any, List, Optional, Tuple

from app.domain import books_domain as bd
from app.domain.dashboard_domain import DashboardDomain
from app.models import Book, SectionFilters


class BooksController:
    def __init__(
        self,
        domain: Optional[bd.BooksDomain] = None,
        dashboard: Optional[DashboardDomain] = None,
    ):
        self.domain = domain if domain is not None else bd.BooksDomain()
        self.dashboard = dashboard if dashboard is not None else DashboardDomain()

    def list_books(self) -> List[Book]:
        return self.domain.list_books()

    def get_book(self, book_id: int) -> Optional[Book]:
        return self.domain.get_book(book_id)

    def create_book(
        self,
        title: str,
        threshold: int,
        short_title: Optional[str] = None,
        category_id: Optional[int] = None,
        opening_stock: Optional[int] = None,
    ) -> Book:
        return self.domain.create_book(
            title=title,
            threshold=threshold,
            short_title=short_title,
            category_id=category_id,
            opening_stock=opening_stock,
        )

    def update_book(self, book_id: int, **fields) -> Optional[Book]:
        return self.domain.update_book(book_id, **fields)

    def delete_book(self, book_id: int) -> bool:
        return self.domain.delete_book(book_id)

    def master_data_add_book(self, payload) -> tuple[Book, bool]:
        return self.domain.master_data_add_book(payload)

    def master_data_page_data(self) -> dict:
        return self.domain.master_data_page_data()

    # ------------------------------------------------------------------
    # Dashboard -- thin pass-through to DashboardDomain. Kept on
    # BooksController (rather than a new router-facing controller)
    # because app/api/routers/dashboard.py already depends on
    # get_books_controller, and this mirrors how SalesController
    # composes multiple domains behind one controller surface.
    # ------------------------------------------------------------------

    def dashboard_data(self, username: str, is_admin: bool, params) -> dict:
        return self.dashboard.get_dashboard_data(username, is_admin, params)

    def leaderboard_export_rows(self, username: str, params) -> Tuple[List[dict], SectionFilters]:
        return self.dashboard.leaderboard_export_rows(username, params)

    def top_books_export_rows(self, username: str, is_admin: bool, params) -> Tuple[List[dict], SectionFilters]:
        return self.dashboard.top_books_export_rows(username, is_admin, params)

    def inventory_export_rows(self, username: str, is_admin: bool, params) -> Tuple[List[dict], SectionFilters]:
        return self.dashboard.inventory_export_rows(username, is_admin, params)
