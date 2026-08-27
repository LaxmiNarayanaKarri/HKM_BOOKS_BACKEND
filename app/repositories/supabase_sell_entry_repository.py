"""
Concrete storage for Sell Entries -- the raw, per-sale-row records
behind the "Books & Sell Entry" page (add a sale, list/filter "My
Recent Entries", export to .xlsx) -- backed by Supabase.

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
    created_at        timestamptz null, default now() at time zone 'utc'

`title`, `location`, and `event` never arrive (or leave) as raw ids --
the Sell Entry form works in book titles / location names, so this
repository resolves those to/from `book_id` / `location_id` via
IBookRepository / ILocationRepository, and only ever talks to `sales`
for what actually lives there.

NOTE on `location` vs `event`: per `SaleCreate` in app/models.py, the
Sell Entry form currently has a single dropdown labelled "Event" whose
value is posted as `location` (and therefore resolved against
ILocationRepository into `location_id`) -- `event`/`event_id` stay
unused until the form grows a second, genuinely separate dropdown. To
keep read/write consistent, `se_event` (the filter parameter on this
same page) is likewise resolved against ILocationRepository rather
than IEventRepository -- filtering by real event_id would always
return nothing today, since nothing populates that column yet. Swap
`_resolve_filter_location_id` back to IEventRepository once a real
second dropdown exists.

`users` (for the filter dropdown) is derived from the distinct
`seller_username` values already on `sales`, rather than calling out
to the Users service -- this repository only owns Books-side data,
and `get_page_data` is a synchronous contract method (see
app/external_services/users_client.py for the async, cross-service
alternative used elsewhere). `recorded_by_name` in the returned rows
is therefore just the username itself for now -- same "no display-name
resolution yet" gap flagged in app/integrations/users_client.py.

ATOMICITY: add_sale inserts the sale row(s) AND decrements `stock` by
the matching qty in a single Postgres transaction (record_sale_batch,
see migrations/sales_atomic_ops.sql) -- mirroring how
record_inward_stock_batch keeps purchases + stock in sync on the
inward side. A sale that would take a book's stock negative is
rejected rather than silently allowed.
"""

from typing import Any, Dict, List, Optional

from app.contracts.book_repository import IBookRepository
from app.contracts.event_repository import IEventRepository
from app.contracts.location_repository import ILocationRepository
from app.contracts.sell_entry_repository import ISellEntryRepository
from app.contracts.stock_repository import IStockRepository
from app.core.errors import ValidationError
from app.injector import DBContract, injector, singleton
from app.models import SaleCreate, SaleRow

TABLE = "sales"

# "My Recent Entries" is a feed, not a full export -- cap it so the
# page load stays fast as the sales table grows. /export ignores this.
_RECENT_ENTRIES_LIMIT = 50


@singleton(ISellEntryRepository)
@injector
class SupabaseSellEntryRepository(ISellEntryRepository):
    """`db`, `book_repo`, `location_repo`, `event_repo`, and
    `stock_repo` are all auto-injected by `@injector` against their
    respective contracts."""

    def __init__(
        self,
        db: DBContract,
        book_repo: IBookRepository,
        location_repo: ILocationRepository,
        event_repo: IEventRepository,
        stock_repo: IStockRepository,
    ):
        self.db = db
        self.book_repo = book_repo
        self.location_repo = location_repo
        self.event_repo = event_repo
        self.stock_repo = stock_repo

    # -- internal helpers -------------------------------------------------
    @property
    def _table(self):
        return self.db.get_client().table(TABLE)

    @staticmethod
    def _normalize(name: str) -> str:
        return (name or "").strip()

    def _resolve_filter_location_id(self, name: str) -> Optional[int]:
        """See module docstring -- `se_event` filters against
        location_id today, mirroring what `location` actually writes."""
        name = self._normalize(name)
        if not name or name.lower() == "all":
            return None
        loc = self.location_repo.find_by_name(name)
        return loc.id if loc else None

    def _resolve_filter_event_id(self, name: str) -> Optional[int]:
        """See module docstring -- `se_event` filters against
        event_id today, mirroring what `event` actually writes."""
        name = self._normalize(name)
        if not name or name.lower() == "all":
            return None
        loc = self.event_repo.find_by_name(name)
        return loc.id if loc else None

    def _resolve_location_id(self, name: str) -> Optional[int]:
        name = self._normalize(name)
        loc = self.location_repo.find_by_name(name) if name else None
        return loc.id if loc else None

    def _resolve_event_id(self, name: str) -> Optional[int]:
        name = self._normalize(name)
        if not name:
            return None
        evt = self.event_repo.find_by_name(name)
        return evt.id if evt else None

    def _book_title_map(self) -> Dict[int, str]:
        return {b.id: b.title for b in self.book_repo.list_all() if b.id is not None}

    def _location_name_map(self) -> Dict[int, str]:
        return {l.id: l.name for l in self.location_repo.list_all() if l.id is not None}

    def _event_name_map(self) -> Dict[int, str]:
        return {l.id: l.name for l in self.event_repo.list_all() if l.id is not None}

    def _book_stock_and_cost(self) -> tuple[Dict[int, int], Dict[int, float]]:
        """
        Reads straight from `stock` (kept current by
        record_inward_stock_batch / record_sale_batch) rather than
        recomputing from purchases/sales/opening_stock. Two reasons:
        cost only lives in `stock.cost` -- there's no way to derive it
        from purchases/sales history -- and the old computation was
        keyed by book *title*, which never actually matched the
        frontend's BOOK_STOCK[titleSelect.value] lookup (that value is
        the book id, per the <option value="{{ t['id'] }}"> in the
        template). Keying by book_id here fixes that.

        CAVEAT: any book whose stock predates the atomic RPCs and was
        never inserted as a `stock` row (e.g. opening_stock that was
        only ever reflected in the old purchases-minus-sales math) will
        show 0/absent here until backfilled.
        """
        stock_by_book: Dict[int, int] = {}
        cost_by_book: Dict[int, float] = {}
        for s in self.stock_repo.list_all():
            if s.book_id is None:
                continue
            stock_by_book[s.book_id] = s.stock or 0
            if s.cost is not None:
                cost_by_book[s.book_id] = s.cost
        return stock_by_book, cost_by_book

    def _row_to_model(
        self,
        row: dict,
        *,
        title_map: Optional[Dict[int, str]] = None,
        location_map: Optional[Dict[int, str]] = None,
    ) -> SaleRow:
        title_map = title_map if title_map is not None else self._book_title_map()
        location_map = location_map if location_map is not None else self._location_name_map()
        event_name = None
        if row.get("event_id") is not None:
            evt = self.event_repo.get(row["event_id"])
            event_name = evt.name if evt else None
        return SaleRow(
            id=row.get("id"),
            sales_date=row["sales_date"],
            book_id=row.get("book_id"),
            category_id=row.get("category_id"),
            seller_username=row.get("seller_username"),
            qty=row.get("qty"),
            cost_price=row.get("cost_price"),
            sell_price=row.get("sell_price"),
            language_id=row.get("language_id"),
            location_id=row.get("location_id"),
            event_id=row.get("event_id"),
            created_at=row.get("created_at"),
            title=title_map.get(row.get("book_id")),
            location_name=location_map.get(row.get("location_id")),
            event_name=event_name,
        )

    def _query_sales(
        self,
        se_user: str,
        se_event: str,
        se_date_from: str,
        se_date_to: str,
        se_location: str,
        *,
        limit: Optional[int] = None,
    ) -> List[dict]:
        filters: dict = {}
        if se_user and se_user != "all":
            filters["seller_username"] = se_user

        location_id = se_location
        if location_id is not None and location_id != 'all':
            filters["location_id"] = location_id

        event_id = se_event
        if event_id is not None and event_id != 'all':
            filters["event_id"] = event_id

        query = self._table.select("*")

        if filters:
            query = query.match(filters)

        if se_date_from and se_date_to:
            query = query.gte("sales_date", se_date_from).lte("sales_date", se_date_to)
        elif se_date_from:
            query = query.gte("sales_date", se_date_from)
        elif se_date_to:
            query = query.lte("sales_date", se_date_to)

        query = query.order("sales_date", desc=True)
        if limit:
            query = query.limit(limit)

        resp = query.execute()
        return resp.data or []

    def _distinct_sellers(self) -> List[str]:
        resp = self._table.select("seller_username").execute()
        seen: List[str] = []
        for row in resp.data or []:
            name = row.get("seller_username")
            if name and name not in seen:
                seen.append(name)
        return sorted(seen)

    # -- ISellEntryRepository -----------------------------------------------
    def get_page_data(
        self,
        username: str,
        se_user: str,
        se_event: str,
        se_date_from: str,
        se_date_to: str,
        se_location: str
    ) -> Dict[str, Any]:
        title_map = self._book_title_map()
        location_map = self._location_name_map()
        event_map = self._event_name_map()

        rows = self._query_sales(se_user, se_event, se_date_from, se_date_to,se_location,limit=_RECENT_ENTRIES_LIMIT)
        my_sales = [
            {
                "date": row.get("sales_date"),
                "title": title_map.get(row.get("book_id"), "(Unknown Book)"),
                "location": location_map.get(row.get("location_id"), ""),
                "event": event_map.get(row.get("event_id"), ""),
                "qty": row.get("qty"),
                "sell_price": row.get("sell_price"),
                "seller": row.get("seller_username"),
                # No cross-service display-name lookup wired up yet --
                # see module docstring.
                "recorded_by_name": row.get("seller_username"),
            }
            for row in rows
        ]

        users = self._distinct_sellers()
        username = self._normalize(username)
        if username and username not in users:
            users.append(username)
            users.sort()

        book_stock, book_cost = self._book_stock_and_cost()
        return {
            "locations": self.location_repo.list_all(),
            "events": self.event_repo.list_all(),
            "book_titles": self.book_repo.list_all(),
            "book_stock": book_stock,
            "book_cost": book_cost,
            "users": users,
            "my_sales": my_sales,
        }

    def add_sale(self, username: str, payload: SaleCreate) -> SaleRow:
        """
        Resolves each item's book (same as before, to snapshot the
        book's current category_id/language_id onto the sale row), then
        inserts every row AND decrements stock for every book in one
        atomic call -- see record_sale_batch in
        migrations/sales_atomic_ops.sql. Do NOT split this back into an
        insert followed by a separate stock update; that's exactly the
        two-call pattern that couldn't be made atomic on the purchases
        side either.
        """
        username = self._normalize(username)
        if not username:
            raise ValidationError("A seller username is required to record a sale.")

        location_id = payload.location
        if location_id is None:
            raise ValidationError(f"Unknown location '{payload.location}'.")

        event_id = payload.event
        if event_id is None:
            raise ValidationError(f"Unknown event '{payload.event}'.")

        title_map = self._book_title_map()
        items: List[Dict[str, Any]] = []
        for item in payload.items:
            if item.qty == 0:
                # Blank rows on the entry form post qty=0 -- skip
                # rather than error, so partial submissions still work.
                continue
            book = self.book_repo.find_by_id(item.title)
            if book is None or book.id is None:
                raise ValidationError(f"Unknown book '{item.title}'. Add it to the catalog first.")
            items.append(
                {
                    "book_id": book.id,
                    "category_id": book.category_id,
                    "language_id": book.language_id,
                    "qty": item.qty,
                    "cost_price": item.cost_price,
                    "sell_price": item.sell_price,
                }
            )
            title_map[book.id] = book.title

        if not items:
            raise ValidationError("At least one book row with a quantity is required.")

        resp = (
            self.db.get_client()
            .rpc("record_sale_batch", {
                "p_items": items,
                "p_sales_date": payload.date.isoformat(),
                "p_seller_username": username,
                "p_location_id": location_id,
                "p_event_id": event_id,
            })
            .execute()
        )
        if resp is None or not resp.data:
            raise RuntimeError("Failed to record sale -- no data returned.")

        location_map = self._location_name_map()
        # Contract: return the created row, or the last one for a
        # multi-item batch, for the caller's confirmation message.
        return self._row_to_model(resp.data[-1], title_map=title_map, location_map=location_map)

    def list_export_rows(
        self,
        username: str,
        se_user: str,
        se_event: str,
        se_date_from: str,
        se_date_to: str,
    ) -> List[Dict[str, Any]]:
        title_map = self._book_title_map()
        location_map = self._location_name_map()
        rows = self._query_sales(se_user, se_event, se_date_from, se_date_to)
        return [
            {
                "date": row.get("sales_date"),
                "title": title_map.get(row.get("book_id"), "(Unknown Book)"),
                "location": location_map.get(row.get("location_id"), ""),
                "qty": row.get("qty"),
                "sell_price": row.get("sell_price"),
                "seller": row.get("seller_username"),
                "recorded_by_name": row.get("seller_username"),
            }
            for row in rows
        ]

    def list_sales_rows(
        self,
        se_user: str = "all",
        se_event: str = "all",
        se_date_from: str = "",
        se_date_to: str = "",
        se_location: str = "all",
        limit: Optional[int] = None,
    ) -> List[SaleRow]:
        """Dashboard-facing counterpart to `list_export_rows` -- same
        underlying `_query_sales`, but returns full `SaleRow` objects
        (cost_price included, no display-field-only trimming) and no
        default row cap, since KPI/leaderboard/top-books math needs
        every matching row, not just the latest 50.

        `se_location`/`se_event` are resolved to ids the same way
        `_query_sales` already expects (it wants id-or-"all" values,
        not names) -- so resolve names to ids here first, mirroring
        `_resolve_filter_location_id` / `_resolve_filter_event_id`.
        """
        location_id: Any = "all"
        if se_location and se_location != "all":
            resolved = self._resolve_location_id(se_location)
            location_id = resolved if resolved is not None else -1

        event_id: Any = "all"
        if se_event and se_event != "all":
            resolved = self._resolve_event_id(se_event)
            event_id = resolved if resolved is not None else -1

        rows = self._query_sales(
            se_user, event_id, se_date_from, se_date_to, location_id, limit=limit
        )
        title_map = self._book_title_map()
        location_map = self._location_name_map()
        return [
            self._row_to_model(row, title_map=title_map, location_map=location_map)
            for row in rows
        ]

    def list_sellers(self) -> List[str]:
        return self._distinct_sellers()