"""
app/domain/dashboard_domain.py

Aggregation layer behind GET /api/dashboard and its three .xlsx export
endpoints (see app/api/routers/dashboard.py). Nothing here talks to
storage directly -- it composes four already-injected repositories
(sales rows, stock, catalog, events) the same way SalesController
composes SalesDomain + SellDomain.

Kept separate from SellDomain (the "Books & Sell Entry" per-row
workflow: recording a sale, "My Recent Entries") and StockDomain (raw
stock CRUD) -- this class only ever produces read-only, aggregated
views: KPI totals, the admin leaderboard, top books, and the inventory
P&L table.

Section-scoped filters
-----------------------
The dashboard template has FOUR independent filter bars sharing one
query string: the page-level one (bare param names -- date_from,
date_to, seller, event) plus three section-level overrides prefixed
`dist_`, `books_`, `inv_` (see `_filters.html`'s `filter_bar(prefix,
...)`). A section falls back to the page-level filter whenever its own
prefixed param is absent, so "just filter the top-books panel" and
"filter everything at once" both work from the same form set.
`_read_filters` implements that fallback for one section at a time.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.contracts.book_repository import IBookRepository
from app.contracts.event_repository import IEventRepository
from app.contracts.purchase_repository import IPurchaseRepository
from app.contracts.sell_entry_repository import ISellEntryRepository
from app.contracts.stock_repository import IStockRepository
from app.injector import injector
from app.models import InventoryRow, SectionFilters, SellerStat, TopBookEntry

_TOP_BOOKS_LIMIT = 10
_LEADERBOARD_LIMIT = 20


def _f(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _q(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _pct(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return (numerator / denominator) * 100.0


@injector
class DashboardDomain:
    """`sell_entry_repo`, `stock_repo`, `book_repo`, `purchase_repo`,
    and `event_repo` are all auto-injected by `@injector` against
    their contracts (see app/container.py for the concrete bindings).
    """

    def __init__(
        self,
        sell_entry_repo: ISellEntryRepository,
        stock_repo: IStockRepository,
        book_repo: IBookRepository,
        purchase_repo: IPurchaseRepository,
        event_repo: IEventRepository,
    ):
        self.sell_entry_repo = sell_entry_repo
        self.stock_repo = stock_repo
        self.book_repo = book_repo
        self.purchase_repo = purchase_repo
        self.event_repo = event_repo

    # ------------------------------------------------------------------
    # Filter parsing
    # ------------------------------------------------------------------

    def _read_filters(self, params, prefix: str = "") -> SectionFilters:
        """Reads `{prefix}date_from` etc., falling back to the bare
        (page-level) param of the same name when the prefixed one is
        missing or blank."""

        def pick(name: str, default: str = "") -> str:
            scoped = (params.get(f"{prefix}{name}") or "").strip()
            if scoped:
                return scoped
            return (params.get(name) or default).strip()

        return SectionFilters(
            date_from=pick("date_from"),
            date_to=pick("date_to"),
            seller=pick("seller", "all") or "all",
            event=pick("event", "all") or "all",
        )

    @staticmethod
    def _window_label(filters: SectionFilters) -> str:
        if not filters.date_from and not filters.date_to:
            return "All time"
        if filters.date_from and filters.date_to:
            return f"{filters.date_from} to {filters.date_to}"
        if filters.date_from:
            return f"Since {filters.date_from}"
        return f"Up to {filters.date_to}"

    # ------------------------------------------------------------------
    # Shared building blocks
    # ------------------------------------------------------------------

    def _sales_rows(self, filters: SectionFilters, *, username: Optional[str] = None):
        """Sale rows matching `filters`, additionally pinned to
        `username` when given (the non-admin "just my sales" case)."""
        seller = username if username else filters.seller
        return self.sell_entry_repo.list_sales_rows(
            se_user=seller or "all",
            se_event=filters.event or "all",
            se_date_from=filters.date_from,
            se_date_to=filters.date_to,
        )

    def _catalog_and_stock(self):
        books = self.book_repo.list_all()
        stock_by_book = {}
        for s in self.stock_repo.list_all():
            if s.book_id is not None:
                stock_by_book[s.book_id] = s
        return books, stock_by_book

    # ------------------------------------------------------------------
    # KPI cluster
    # ------------------------------------------------------------------

    def _kpis(self, rows) -> Dict[str, float]:
        qty = sum(_q(r.qty) for r in rows)
        cost = sum(_q(r.qty) * _f(r.cost_price) for r in rows)
        revenue = sum(_q(r.qty) * _f(r.sell_price) for r in rows)
        return {"qty": qty, "cost": cost, "revenue": revenue}

    # ------------------------------------------------------------------
    # Leaderboard (admin only -- "Top Distributors")
    # ------------------------------------------------------------------

    def _leaderboard(self, rows) -> List[SellerStat]:
        by_seller: Dict[str, SellerStat] = {}
        for r in rows:
            seller = r.seller_username or "(Unknown)"
            stat = by_seller.setdefault(seller, SellerStat(seller=seller, revenue=0.0, profit=0.0, qty=0))
            qty = _q(r.qty)
            revenue = qty * _f(r.sell_price)
            cost = qty * _f(r.cost_price)
            stat.revenue += revenue
            stat.profit += revenue - cost
            stat.qty += qty
        ordered = sorted(by_seller.values(), key=lambda s: s.revenue, reverse=True)
        return ordered[:_LEADERBOARD_LIMIT]

    # ------------------------------------------------------------------
    # Top books
    # ------------------------------------------------------------------

    def _top_books(self, rows) -> List[TopBookEntry]:
        by_title: Dict[str, TopBookEntry] = {}
        for r in rows:
            title = r.title or "(Unknown Book)"
            entry = by_title.setdefault(title, TopBookEntry(title=title, qty=0, profit=0.0))
            qty = _q(r.qty)
            revenue = qty * _f(r.sell_price)
            cost = qty * _f(r.cost_price)
            entry.qty += qty
            entry.profit += revenue - cost
        ordered = sorted(by_title.values(), key=lambda e: e.qty, reverse=True)
        return ordered[:_TOP_BOOKS_LIMIT]

    # ------------------------------------------------------------------
    # Inventory (Book Inventory Updates)
    # ------------------------------------------------------------------

    def _inventory(self, filters: SectionFilters) -> List[InventoryRow]:
        books, stock_by_book = self._catalog_and_stock()

        purchases = self.purchase_repo.list_filtered(
            date_from=self._parse_date(filters.date_from),
            date_to=self._parse_date(filters.date_to),
        )
        received_qty: Dict[int, int] = {}
        received_cost: Dict[int, float] = {}
        for p in purchases:
            if p.book_id is None:
                continue
            received_qty[p.book_id] = received_qty.get(p.book_id, 0) + _q(p.qty)
            received_cost[p.book_id] = received_cost.get(p.book_id, 0.0) + _q(p.qty) * _f(p.cost_price)

        sale_rows = self._sales_rows(SectionFilters(filters.date_from, filters.date_to, "all", filters.event))
        sold_qty: Dict[int, int] = {}
        sold_revenue: Dict[int, float] = {}
        sold_cost: Dict[int, float] = {}
        for r in sale_rows:
            if r.book_id is None:
                continue
            qty = _q(r.qty)
            sold_qty[r.book_id] = sold_qty.get(r.book_id, 0) + qty
            sold_revenue[r.book_id] = sold_revenue.get(r.book_id, 0.0) + qty * _f(r.sell_price)
            sold_cost[r.book_id] = sold_cost.get(r.book_id, 0.0) + qty * _f(r.cost_price)

        rows: List[InventoryRow] = []
        for book in books:
            if book.id is None:
                continue
            stock = stock_by_book.get(book.id)
            available = _q(stock.stock) if stock else 0
            live_cost = _f(stock.cost) if stock and stock.cost is not None else 0.0

            r_qty = received_qty.get(book.id, 0)
            r_cost_total = received_cost.get(book.id, 0.0)
            s_qty = sold_qty.get(book.id, 0)
            s_revenue = sold_revenue.get(book.id, 0.0)
            s_cost = sold_cost.get(book.id, 0.0)

            avg_cost = (r_cost_total / r_qty) if r_qty else live_cost
            avg_sell = (s_revenue / s_qty) if s_qty else 0.0
            profit_or_loss = s_revenue - s_cost
            pl_pct = _pct(profit_or_loss, s_cost)

            initial_stock = available - r_qty + s_qty

            rows.append(
                InventoryRow(
                    title=book.title,
                    category=str(book.category_id) if book.category_id else "",
                    initial_stock=initial_stock,
                    received=r_qty,
                    sold=s_qty,
                    available=available,
                    threshold=book.threshold or 0,
                    below_threshold=available <= (book.threshold or 0),
                    avg_cost=avg_cost,
                    avg_sell=avg_sell,
                    profit_or_loss=profit_or_loss,
                    pl_pct=pl_pct,
                )
            )

        rows.sort(key=lambda r: r.title.lower())
        return rows

    @staticmethod
    def _parse_date(value: str) -> Optional[date]:
        value = (value or "").strip()
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _total_available(inventory: List[InventoryRow]) -> int:
        return sum(r.available for r in inventory)

    # ------------------------------------------------------------------
    # Public: page data
    # ------------------------------------------------------------------

    def get_dashboard_data(self, username: str, is_admin: bool, params) -> Dict[str, Any]:
        overview_filters = self._read_filters(params, "")
        dist_filters = self._read_filters(params, "dist_")
        books_filters = self._read_filters(params, "books_")
        inv_filters = self._read_filters(params, "inv_")

        kpi_rows = self._sales_rows(overview_filters, username=None if is_admin else username)
        kpis = self._kpis(kpi_rows)
        net_pl = kpis["revenue"] - kpis["cost"]
        pl_pct = _pct(net_pl, kpis["cost"])

        inventory = self._inventory(inv_filters)
        total_available = self._total_available(inventory)

        leaderboard: List[Dict[str, Any]] = []
        if is_admin:
            dist_rows = self._sales_rows(dist_filters)
            leaderboard = [
                {"seller": s.seller, "revenue": s.revenue, "qty": s.qty, "profit": s.profit}
                for s in self._leaderboard(dist_rows)
            ]

        books_rows = self._sales_rows(books_filters, username=None if is_admin else username)
        my_top_books = [
            {"title": b.title, "qty": b.qty, "profit": b.profit}
            for b in self._top_books(books_rows)
        ]

        sellers = self.sell_entry_repo.list_sellers()
        events = [e.name for e in self.event_repo.list_all()]

        return {
            "kpis": kpis,
            "net_pl": net_pl,
            "pl_pct": pl_pct,
            "total_available": total_available,
            "leaderboard": leaderboard,
            "my_top_books": my_top_books,
            "inventory": [vars(r) for r in inventory],
            "filters": vars(overview_filters),
            "sellers": sellers,
            "events": events,
            "window_label": self._window_label(overview_filters),
            "is_admin": is_admin,
        }

    # ------------------------------------------------------------------
    # Public: exports
    # ------------------------------------------------------------------

    def leaderboard_export_rows(self, username: str, params) -> Tuple[List[Dict[str, Any]], SectionFilters]:
        filters = self._read_filters(params, "dist_")
        rows = self._sales_rows(filters)
        data = [
            {"seller": s.seller, "revenue": s.revenue, "qty": s.qty, "profit": s.profit}
            for s in self._leaderboard(rows)
        ]
        return data, filters

    def top_books_export_rows(self, username: str, is_admin: bool, params) -> Tuple[List[Dict[str, Any]], SectionFilters]:
        filters = self._read_filters(params, "books_")
        rows = self._sales_rows(filters, username=None if is_admin else username)
        data = [{"title": b.title, "qty": b.qty} for b in self._top_books(rows)]
        return data, filters

    def inventory_export_rows(self, username: str, is_admin: bool, params) -> Tuple[List[Dict[str, Any]], SectionFilters]:
        filters = self._read_filters(params, "inv_")
        inventory = self._inventory(filters)
        data = [
            {
                "title": r.title,
                "available": r.available,
                "threshold": r.threshold,
                "avg_cost": r.avg_cost,
                "avg_sell": r.avg_sell,
                "profit_or_loss": r.profit_or_loss,
                "pl_pct": r.pl_pct,
            }
            for r in inventory
        ]
        return data, filters
