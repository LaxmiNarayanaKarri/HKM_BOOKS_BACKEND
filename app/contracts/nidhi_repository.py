"""
Contract for Nidhi (fund) persistence. `NidhiDomain` only ever talks to
this interface -- never to Supabase, blob storage, or any other
concrete engine directly. Balances are scoped per user_id.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.models import NidhiBalance, NidhiFundType, NidhiTransaction


class INidhiRepository(ABC):

    @abstractmethod
    def get_balances(self, user_id: str) -> NidhiBalance:
        """This user's current balances for both funds. Returns a
        zeroed NidhiBalance if the user has no row yet."""

    @abstractmethod
    def adjust_balance(
        self, user_id: str, fund_type: NidhiFundType, amount: float
    ) -> float:
        """Atomically add `amount` (negative to subtract) to this user's
        balance for `fund_type`. Creates the user's row if it doesn't
        exist yet. Returns the new balance."""

    @abstractmethod
    def add_transaction(self, txn: NidhiTransaction) -> NidhiTransaction:
        """Insert a transaction row. Implementations should stamp
        `balance_after` from the user's current balance for that fund."""

    @abstractmethod
    def get_transaction(self, transaction_id: str) -> Optional[NidhiTransaction]:
        ...

    @abstractmethod
    def update_transaction(self, transaction_id: str, **fields) -> Optional[NidhiTransaction]:
        """Patch arbitrary fields (status, decided_by, decided_at,
        decision_note, ...). Implementations should stamp
        `balance_after` when status transitions to APPROVED."""

    @abstractmethod
    def list_transactions(self, limit: int = 10, archived: bool = False) -> List[NidhiTransaction]:
        """Org-wide feed across all users (for admin/dashboard views)."""

    @abstractmethod
    def list_transactions_for_user(
        self, user_id: str, limit: int = 50, archived: bool = False
    ) -> List[NidhiTransaction]:
        """Transactions raised by the user in requested_by."""

    @abstractmethod
    def list_pending(self) -> List[NidhiTransaction]:
        """Org-wide pending requests (for approvers)."""