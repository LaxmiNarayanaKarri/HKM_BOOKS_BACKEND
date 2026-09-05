"""
Pydantic models for the Books domain (catalog, sales ledger, inward
stock/purchases).

These validate input at the API boundary. Internally, the in-memory
store still works with plain dicts (see db/db.py) -- analytics math over
a few thousand sale rows is simpler and faster on dicts than on frozen
pydantic instances, and this is exactly the kind of hot, high-volume
path where that tradeoff is worth it. Pydantic guards the door; dicts do
the arithmetic once inside.

Convention: `XCreate` = a `BaseModel` describing what the API accepts as
input; the bare name (`Book`, `SaleRecord`, ...) = a `dataclass`
describing what the domain layer works with and hands back out. The
original file accidentally declared `Book` twice (once as each) -- this
keeps only the dataclass form, matching every other pair below.
"""

from dataclasses import field
import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime, timezone
from pydantic.dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# API input schemas  (XCreate / XUpdate)
# ---------------------------------------------------------------------------

class BookCreate(BaseModel):
    title: str = Field(min_length=1)
    short_title: str = ""
    category: str = ""
    language: str = ""
    threshold: Optional[int] = None


class ThresholdUpdate(BaseModel):
    title: str = Field(min_length=1)
    threshold: int = Field(ge=0)


class NameCreate(BaseModel):
    """Generic {"name": "..."} payload for categories/languages/locations/events."""

    name: str = Field(min_length=1)


class SaleCreate(BaseModel):
    date: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: str = ""
    qty: int = Field(gt=0)
    cost_price: float = Field(ge=0)
    sell_price: float = Field(ge=0)
    language: str = Field(min_length=1)
    location: str = Field(min_length=1)


class PurchaseRowCreate(BaseModel):
    title: str = Field(min_length=1)
    short_title: str = ""
    category: str = ""
    language: str = ""
    qty: int = Field(gt=0)
    cost_price: float = Field(ge=0)


class PurchaseBatchCreate(BaseModel):
    """Replaces the old Flask form's parallel `title[]`/`qty[]`/...
    arrays (an HTML-form artifact) with a plain list of rows, which is
    the natural JSON-API shape for a "batch of purchased books" input."""

    purchase_date: str = Field(min_length=1)
    source: str = Field(min_length=1)
    rows: List[PurchaseRowCreate] = Field(default_factory=list)
    

# --- Add to app/models.py ---

from typing import Optional
from pydantic import BaseModel


class Stock(BaseModel):
    """
    Mirrors public.stock:
        id        bigint  identity, PK
        book_id   bigint  FK -> catalog.id
        stock     bigint  quantity on hand
        cost      bigint  unit cost
    """
    id: Optional[int] = None
    book_id: Optional[int] = None
    stock: Optional[int] = None
    cost: Optional[int] = None

class StockDelta:
    """book_id + signed qty change, e.g. StockDelta(book_id=7, delta=5)."""

    def __init__(self, book_id: int, delta: int):
        self.book_id = book_id
        self.delta = delta


# ---------------------------------------------------------------------------
# Domain dataclasses  (what the domain layer works with internally)
# ---------------------------------------------------------------------------

@dataclass
class SaleRecord:
    id: int
    date: str
    title: str
    category: str
    seller: str
    qty: int
    cost_price: float
    sell_price: float
    language: str = ""
    location: str = ""

    @property
    def revenue(self) -> float:
        return self.sell_price * self.qty

    @property
    def cost(self) -> float:
        return self.cost_price * self.qty

    @property
    def profit(self) -> float:
        return self.revenue - self.cost


@dataclass
class PurchaseRecord:
    id: int
    date: str
    title: str
    short_title: str
    category: str
    language: str
    source: str
    qty: int
    cost_price: float
    recorded_by: str

    @property
    def total_cost(self) -> float:
        return self.qty * self.cost_price


@dataclass
class SectionFilters:
    date_from: str
    date_to: str
    seller: str
    event: str


@dataclass
class SalesSummary:
    orders: int
    qty: int
    revenue: float
    cost: float
    profit: float
    loss: float


@dataclass
class TrendSeries:
    labels: List[str] = field(default_factory=list)
    revenue: List[float] = field(default_factory=list)
    cost: List[float] = field(default_factory=list)
    profit: List[float] = field(default_factory=list)


@dataclass
class CategoryBreakdown:
    labels: List[str] = field(default_factory=list)
    values: List[float] = field(default_factory=list)


@dataclass
class SellerStat:
    seller: str
    revenue: float
    profit: float
    qty: int


@dataclass
class LocationStat:
    location: str
    revenue: float
    profit: float
    qty: int
    orders: int


@dataclass
class TopBookEntry:
    title: str
    qty: int
    profit: float


@dataclass
class InventoryRow:
    title: str
    category: str
    initial_stock: int
    received: int
    sold: int
    available: int
    threshold: int
    below_threshold: bool
    avg_cost: float
    avg_sell: float
    profit_or_loss: float
    pl_pct: float


@dataclass
class BackupDay:
    date: str
    has_records: bool


# ---------------------------------------------------------------------------
# Stored-record models  (what repositories hand back out — BaseModel so
# they serialise cleanly via .model_dump() / FastAPI response_model)
# ---------------------------------------------------------------------------

class Book(BaseModel):
    id: Optional[int] = None
    title: str
    short_title: Optional[str] = None
    category_id: Optional[int] = None
    language_id: Optional[int] = None
    threshold: int = 0
    opening_stock: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Location(BaseModel):
    id: Optional[int] = None
    name: str
    created_at: Optional[datetime] = None


class Category(BaseModel):
    id: Optional[int] = None
    name: str
    created_at: Optional[datetime] = None

class Source(BaseModel):
    id: Optional[int] = None
    name: str
    created_at: Optional[datetime] = None

class Language(BaseModel):
    id: Optional[int] = None
    name: str
    created_at: Optional[datetime] = None


class Event(BaseModel):
    id: Optional[int] = None
    name: str
    created_at: Optional[datetime] = None


class Purchase(BaseModel):
    id: Optional[int] = None
    book_id: int
    source_id: int
    recorded_by: str
    purchase_date: date                   
    created_at: Optional[datetime] = None
    qty: int = Field(gt=0)
    cost_price: float = Field(ge=0)

    @property
    def total_cost(self) -> Optional[float]:
        if self.qty is None or self.cost_price is None:
            return None
        return round(self.qty * self.cost_price, 2)
    
    @field_validator("created_at", mode="before")
    @classmethod
    def _normalize_offset(cls, v):
        """
        Postgres's default text output for a timestamptz with a
        whole-hour UTC offset drops the minutes -- '...+00' instead of
        '...+00:00' -- which pydantic's strict ISO-8601 parser rejects
        ("unexpected extra characters at the end of the input"). The
        newer inventory RPC functions format created_at explicitly with
        a 'Z' suffix to avoid this, but any row written before that fix
        (or by a path that still does a plain ::text cast) can still
        carry the bare-offset form. Normalize defensively here instead
        of relying on every write path getting the format right.
        """
        if isinstance(v, str):
            v = re.sub(r'([+-]\d{2})$', r'\1:00', v)
        return v


class PurchaseItemCreate(BaseModel):
    book_id: int 
    recorded_by: Optional[str] = None
    created_at: Optional[datetime] = None
    qty: int = Field(gt=0)
    cost_price: float = Field(ge=0)


class PurchaseBatchCreate(BaseModel):
    purchase_date: date
    items: List[PurchaseItemCreate] = Field(default_factory=list)
    source_id: int


class SaleItem(BaseModel):
    """One book line within a sale submission -- mirrors a single
    <tr class="book-row"> on the Sell Entry form (title[], qty[],
    cost_price[], sell_price[])."""
 
    title: str
    qty: int = Field(ge=0)
    cost_price: float = Field(ge=0)
    sell_price: float = Field(ge=0)
 
    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Book title is required.")
        return v
 
 
class SaleCreate(BaseModel):
    """POST /api/sell request body -- one batch of book rows recorded
    against a single date + location/event.
 
    NOTE: the current Sell Entry form only has one dropdown ("Event",
    posted as `location`). The `sales` table has both location_id and
    event_id as separate columns, so `event` is included here as
    optional for when/if the form grows a second dropdown -- until
    then it will just be None and event_id will be left null on
    insert.
    """
 
    date: date
    location: str
    event: Optional[str] = None
    items: List[SaleItem]
 
    @field_validator("location")
    @classmethod
    def location_must_not_be_blank(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Location/event is required.")
        return v
 
    @field_validator("items")
    @classmethod
    def items_must_not_be_empty(cls, v: List[SaleItem]) -> List[SaleItem]:
        if not v:
            raise ValueError("At least one book row is required.")
        return v
 
 
class SaleRow(BaseModel):
    """A single stored sale record, matching the real `sales` table
    columns. `title`, `location_name`, and `event_name` are NOT
    columns on the table -- they're populated by the repository after
    resolving the FK ids, purely for display in "My Recent Entries"
    and the .xlsx export."""
 
    id: Optional[int] = None
    sales_date: date
    book_id: Optional[int] = None
    category_id: Optional[int] = None
    seller_username: Optional[str] = None
    qty: Optional[int] = None
    cost_price: Optional[float] = None
    sell_price: Optional[float] = None
    language_id: Optional[int] = None
    location_id: Optional[int] = None
    event_id: Optional[int] = None
    created_at: Optional[str] = None
 
    # Display-only, resolved by the repository -- not real columns.
    title: Optional[str] = None
    location_name: Optional[str] = None
    event_name: Optional[str] = None
 
    model_config = {"populate_by_name": True}
    
    
class NidhiFundType(str, Enum):
    TIRTHA_NIDHI = "tirtha_nidhi"
    CONTRIBUTION_NIDHI = "contribution_nidhi"
 
 
class NidhiTransactionType(str, Enum):
    CONTRIBUTION = "contribution"
    REDEMPTION = "redemption"
 
 
class NidhiTransactionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


@dataclass
class BookRequest:
    book_id: int
    quantity: int
    location_id: int
    event_id: int
    priority: str
    requested_by: str
    status: str = "pending"
    id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
 
 
@dataclass
class NidhiBalance:
    user_id: str
    tirtha_balance: float
    contribution_balance: float
    updated_at: Optional[datetime] = None

    def for_fund(self, fund_type: NidhiFundType) -> float:
        return (
            self.tirtha_balance
            if fund_type == NidhiFundType.TIRTHA_NIDHI
            else self.contribution_balance
        )


@dataclass
class NidhiTransaction:
    user_id: str
    fund_type: NidhiFundType
    type: NidhiTransactionType
    amount: float
    requested_by: str
    status: NidhiTransactionStatus
    created_at: datetime
    id: Optional[str] = None
    balance_after: Optional[float] = None
    tirtha_amount: float = 0.0
    contribution_amount: float = 0.0
    note: Optional[str] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    decision_note: Optional[str] = None
    archived: bool = False
    
class RedemptionDecisionRequest(BaseModel):
    amount: Optional[float] = None
    fund_type: Optional[NidhiFundType] = None
    tirtha_amount: Optional[float] = None
    contribution_amount: Optional[float] = None
    user_id: Optional[str] = None          # admin correcting who it's for
    reason: Optional[str] = None           # used on reject only


class ContributeRequest(BaseModel):
    user_id: str
    fund_type: NidhiFundType
    amount: float
    note: Optional[str] = None

class RedeemRequest(BaseModel):
    user_id: str
    fund_type: NidhiFundType
    amount: float
    note: Optional[str] = None   # Flask should send `note`, not `reason` (below)