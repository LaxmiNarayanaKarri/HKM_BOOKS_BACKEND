"""
Concrete storage for the Nidhi (fund) domain, backed by Supabase (Postgres).

This is the ONLY file that knows `nidhi_balances` / `nidhi_transactions`
tables exist, or what their columns are. `NidhiDomain` never talks to
Supabase directly, only to the `INidhiRepository` contract.

Balances are per-user: `nidhi_balances.user_id` is the primary key, with
`tirtha_nidhi_balance` and `contribution_nidhi_balance` as sibling columns
on that same row (see schema.sql, including the adjust_nidhi_balance() RPC).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.contracts.nidhi_repository import INidhiRepository
from app.injector import DBContract, injector, singleton
from app.models import (
    NidhiBalance,
    NidhiFundType,
    NidhiTransaction,
    NidhiTransactionStatus,
    NidhiTransactionType,
)

BALANCES_TABLE = "nidhi_balances"
TXN_TABLE = "nidhi_transactions"


@singleton(INidhiRepository)
@injector
class SupabaseNidhiRepository(INidhiRepository):
    """`db` (a `DBContract`) is auto-injected by `@injector`. Pass a fake
    explicitly (`SupabaseNidhiRepository(db=FakeDB())`) to unit-test this
    class without touching a real database."""

    def __init__(self, db: DBContract):
        self.db = db

    # -- internal helpers -------------------------------------------------
    @property
    def _balances(self):
        return self.db.get_client().table(BALANCES_TABLE)

    @property
    def _txns(self):
        return self.db.get_client().table(TXN_TABLE)

    @staticmethod
    def _to_balance(user_id: str, row: Optional[dict]) -> NidhiBalance:
        if not row:
            return NidhiBalance(
                user_id=user_id,
                tirtha_balance=0.0,
                contribution_balance=0.0,
                updated_at=None,
            )
        return NidhiBalance(
            user_id=row["user_id"],
            tirtha_balance=row.get("tirtha_nidhi_balance", 0.0),
            contribution_balance=row.get("contribution_nidhi_balance", 0.0),
            updated_at=(
                datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else None
            ),
        )

    @staticmethod
    def _to_transaction(row: dict) -> NidhiTransaction:
        amount = row["amount"]
        fund_type = NidhiFundType(row["fund_type"])
        tirtha_amount = row.get("tirtha_amount")
        contribution_amount = row.get("contribution_amount")
        # Older rows predate the split columns; derive their value from the
        # original fund and amount so history remains complete.
        if tirtha_amount is None and contribution_amount is None:
            tirtha_amount = amount if fund_type == NidhiFundType.TIRTHA_NIDHI else 0
            contribution_amount = amount if fund_type == NidhiFundType.CONTRIBUTION_NIDHI else 0
        return NidhiTransaction(
            id=row["id"],
            user_id=row["user_id"],
            fund_type=fund_type,
            # FIX: was `type=row["type"]` (left as a raw string), which
            # broke every `txn.type.value` call downstream (domain
            # filtering, templates). fund_type/status were already
            # correctly re-wrapped here -- type wasn't.
            type=NidhiTransactionType(row["type"]),
            amount=amount,
            balance_after=row.get("balance_after"),
            tirtha_amount=tirtha_amount or 0,
            contribution_amount=contribution_amount or 0,
            note=row.get("note"),
            requested_by=row["requested_by"],
            status=NidhiTransactionStatus(row["status"]),
            decided_by=row.get("decided_by"),
            decided_at=(
                datetime.fromisoformat(row["decided_at"]) if row.get("decided_at") else None
            ),
            decision_note=row.get("decision_note"),
            archived=row.get("archived", False),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _current_balance(self, user_id: str, fund_type: NidhiFundType) -> float:
        balances = self.get_balances(user_id)
        return balances.for_fund(fund_type)

    # -- INidhiRepository ---------------------------------------------------
    def get_balances(self, user_id: str) -> NidhiBalance:
        resp = (
            self._balances.select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return self._to_balance(user_id, rows[0] if rows else None)

    def adjust_balance(
        self, user_id: str, fund_type: NidhiFundType, amount: float
    ) -> float:
        resp = self.db.get_client().rpc(
            "adjust_nidhi_balance",
            {
                "p_user_id": user_id,
                "p_fund_type": fund_type.value,
                "p_amount": amount,
            },
        ).execute()
        if resp is None or resp.data is None:
            raise RuntimeError(
                f"Failed to adjust balance for user '{user_id}', fund '{fund_type.value}'."
            )
        return resp.data  # the RPC returns the new balance directly

    def add_transaction(self, txn: NidhiTransaction) -> NidhiTransaction:
        payload: Dict[str, Any] = {
            "user_id": txn.user_id,
            "fund_type": txn.fund_type.value,
            "type": txn.type.value if hasattr(txn.type, "value") else txn.type,
            "amount": txn.amount,
            "tirtha_amount": txn.tirtha_amount if txn.tirtha_amount else (
                txn.amount if txn.fund_type == NidhiFundType.TIRTHA_NIDHI else 0
            ),
            "contribution_amount": txn.contribution_amount if txn.contribution_amount else (
                txn.amount if txn.fund_type == NidhiFundType.CONTRIBUTION_NIDHI else 0
            ),
            "note": txn.note,
            "requested_by": txn.requested_by,
            "status": txn.status.value,
            "created_at": txn.created_at.isoformat(),
            # Stamp balance_after from this user's current balance for the
            # fund. For COMPLETED rows the domain always calls
            # adjust_balance() before add_transaction(), so this reflects
            # the post-adjustment balance. For PENDING contribution/
            # redemption requests it just reflects today's balance
            # (nothing moved yet -- that only happens on approval).
            "balance_after": self._current_balance(txn.requested_by, txn.fund_type),
        }
        resp = self._txns.insert(payload).select().execute()
        if resp is None or not resp.data:
            raise RuntimeError("Failed to insert Nidhi transaction — no data returned.")
        return self._to_transaction(resp.data[0])

    def get_transaction(self, transaction_id: str) -> Optional[NidhiTransaction]:
        resp = self._txns.select("*").eq("id", transaction_id).limit(1).execute()
        rows = resp.data or []
        return self._to_transaction(rows[0]) if rows else None

    def update_transaction(self, transaction_id: str, **fields) -> Optional[NidhiTransaction]:
        if not fields:
            return self.get_transaction(transaction_id)

        patch: Dict[str, Any] = {}
        for key, value in fields.items():
            if key == "status" and hasattr(value, "value"):
                patch[key] = value.value
            # FIX: admin redemption review can now edit fund_type (see
            # NidhiDomain.approve_redemption) -- without this branch an
            # enum member would be sent straight to Postgres and fail
            # to serialize the same way status/fund_type already needed
            # explicit handling everywhere else in this file.
            elif key == "fund_type" and hasattr(value, "value"):
                patch[key] = value.value
            elif key == "decided_at" and isinstance(value, datetime):
                patch[key] = value.isoformat()
            else:
                patch[key] = value

        # When a redemption is approved, the balance has already moved
        # (NidhiDomain.approve_redemption calls adjust_balance() first,
        # against the possibly-corrected user_id/fund_type/amount) --
        # stamp balance_after now so the transaction row reflects it.
        # Same for an approved contribution (NidhiDomain.approve_contribution
        # also adjusts the balance before this call).
        if patch.get("status") == NidhiTransactionStatus.APPROVED.value:
            existing = self.get_transaction(transaction_id)
            if existing:
                patch["balance_after"] = self._current_balance(
                    existing.requested_by, existing.fund_type
                )

        if ("amount" in patch or "fund_type" in patch) and not {
            "tirtha_amount", "contribution_amount"
        }.intersection(patch):
            existing = self.get_transaction(transaction_id)
            if existing:
                updated_amount = patch.get("amount", existing.amount)
                updated_fund = patch.get("fund_type", existing.fund_type)
                if isinstance(updated_fund, str):
                    updated_fund = NidhiFundType(updated_fund)
                patch["tirtha_amount"] = (
                    updated_amount if updated_fund == NidhiFundType.TIRTHA_NIDHI else 0
                )
                patch["contribution_amount"] = (
                    updated_amount if updated_fund == NidhiFundType.CONTRIBUTION_NIDHI else 0
                )

        resp = self._txns.update(patch).eq("id", transaction_id).execute()
        rows = resp.data or []
        return self._to_transaction(rows[0]) if rows else self.get_transaction(transaction_id)

    def list_transactions(self, limit: int = 10, archived: bool = False) -> List[NidhiTransaction]:
        resp = (
            self._txns.select("*")
            .eq("archived", archived)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [self._to_transaction(r) for r in (resp.data or [])]

    def list_transactions_for_user(
        self, user_id: str, limit: int = 50, archived: bool = False
    ) -> List[NidhiTransaction]:
        resp = (
            self._txns.select("*")
            .eq("requested_by", user_id)
            .eq("archived", archived)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [self._to_transaction(r) for r in (resp.data or [])]

    def list_pending(self) -> List[NidhiTransaction]:
        resp = (
            self._txns.select("*")
            .eq("status", NidhiTransactionStatus.PENDING.value)
            .order("created_at")
            .execute()
        )
        return [self._to_transaction(r) for r in (resp.data or [])]