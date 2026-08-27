"""
Controller for the inward-stock feature. Composes PurchasesDomain with
the reference-data domains (Books, Categories, Languages) to serve the
/api/inward-stock endpoints. `source` is plain free text on Purchase —
no domain/lookup table for it (yet).
 
# ASSUMPTION: BooksDomain / CategoriesDomain / LanguagesDomain exist
# with `find_by_name` + `create_*` methods, mirroring LocationsDomain.
# Rename to match your actual domain classes/methods if they differ.
"""
 
from datetime import date
from typing import List, Optional
 
from starlette.datastructures import QueryParams
 
from app.domain.books_domain import BooksDomain
from app.domain.categories_domain import CategoriesDomain
from app.domain.languages_domain import LanguagesDomain
from app.domain.purchases_domain import PurchasesDomain
from app.domain.sources_domain import SourcesDomain
from app.models import Purchase, PurchaseBatchCreate
 
 
 
class PurchasesController:
    def __init__(
        self,
        purchases: Optional[PurchasesDomain] = None,
        books: Optional[BooksDomain] = None,
        categories: Optional[CategoriesDomain] = None,
        languages: Optional[LanguagesDomain] = None,
        sources: Optional[SourcesDomain] = None,
    ):
        self.purchases = purchases if purchases is not None else PurchasesDomain()
        self.books = books if books is not None else BooksDomain()
        self.categories = categories if categories is not None else CategoriesDomain()
        self.languages = languages if languages is not None else LanguagesDomain()
        self.sources = sources if sources is not None else SourcesDomain()
 
    # -- shared filter parsing ---------------------------------------------
    @staticmethod
    def _parse_filters(query_params: QueryParams):
        date_from_raw = query_params.get("pf_date_from")
        date_to_raw = query_params.get("pf_date_to")
        recorded_by = query_params.get("pf_recorded_by")
        book_id_raw = query_params.get("pf_book")
 
        return {
            "date_from": date.fromisoformat(date_from_raw) if date_from_raw else None,
            "date_to": date.fromisoformat(date_to_raw) if date_to_raw else None,
            "recorded_by": recorded_by if recorded_by and recorded_by != "all" else None,
            "book_id": int(book_id_raw) if book_id_raw and book_id_raw != "all" else None,
        }
 
    def _resolve_or_create(self, domain, name: str):
        """Find an existing reference row by name, or create it if it
        doesn't exist yet. Returns None for a blank name."""
        name = (name or "").strip()
        if not name:
            return None
        existing = domain.find_by_name(name)
        if existing:
            return existing
        create_fn = getattr(domain, "create_category", None) \
            or getattr(domain, "create_language", None) \
            or getattr(domain, "create", None)
        return create_fn(name) if create_fn else None
 
    def _join_row(self, p: Purchase) -> dict:
        book = self.books.get_book(p.book_id) if p.book_id else None
        category_id = getattr(book, "category_id", None)
        language_id = getattr(book, "language_id",None)
        category = self.categories.get_category(category_id) if category_id else None
        language = self.languages.get_language(language_id) if language_id else None
        source = self.sources.get_source(p.source_id) if p.source_id else None
        return {
            "date": p.purchase_date,
            "title": getattr(book, "title", None),
            "short_title": getattr(book,"short_title",None),
            "category": getattr(category, "name", None),
            "language": getattr(language, "name", None),
            "source": getattr(source, "name", None) ,
            "qty": p.qty,
            "cost_price": p.cost_price,
            "total_cost": p.total_cost,
            "recorded_by": p.recorded_by
        }
 
    # -- GET /api/inward-stock ----------------------------------------------
    def _book_row(self, book) -> dict:
        category = self.categories.get_category(book.category_id) if book.category_id else None
        return {
            "title": book.title,
            "short_title": book.short_title,
            "category": getattr(category, "name", None),
            "id": book.id,
        }
 
    # -- GET /api/inward-stock ----------------------------------------------
    def inward_stock_page_data(self, query_params: QueryParams) -> dict:
        filters = self._parse_filters(query_params)
        recent = self.purchases.recent_purchases(**filters, limit=50)
        return {
            "categories": self.categories.list_categories(),
            "languages": self.languages.list_languages(),
            "recent_purchases": [self._join_row(p) for p in recent],
            "sources": self.sources.list_sources(),
            "book_catalog": [self._book_row(b) for b in self.books.list_books()],
        }
 
    # -- POST /api/inward-stock ----------------------------------------------
    def record_inward_stock(self, user_name: str, payload: PurchaseBatchCreate) -> int:
        """
        Delegates straight to PurchasesDomain.record_inward_stock, which
        builds the items and inserts purchases + adjusts stock in one
        atomic call. Do NOT reintroduce a separate stock-adjustment call
        here -- record_batch/record_inward_stock on the domain already
        apply stock as part of the same transaction; calling a stock
        domain afterwards double-counts every quantity.
        """
        return self.purchases.record_inward_stock(user_name, payload)
 
    # -- GET /api/inward-stock/export ----------------------------------------
    def export_inward_stock_rows(self, query_params: QueryParams) -> List[dict]:
        filters = self._parse_filters(query_params)
        rows = self.purchases.recent_purchases(**filters)
        return [self._join_row(p) for p in rows]
 
