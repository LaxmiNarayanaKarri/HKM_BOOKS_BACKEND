"""
Nidhi domain logic. `user_id` is always whose balance/fund is affected.
`performed_by` is whoever is actually operating the UI (may differ from
`user_id`, e.g. someone entering a contribution on a devotee's behalf).

Two decision flows, deliberately kept separate:

  Contribution -> created PENDING -> only `user_id` (the recipient) may
      approve/reject it, via approve_contribution/reject_contribution.
      No fields are editable at decision time. Approval credits the fund.

  Redemption -> created PENDING -> any admin (nidhi_approve permission,
      enforced at the router) may review ALL pending redemptions via
      approve_redemption/reject_redemption, and may correct amount /
      fund_type / user_id before approving. Approval debits the fund.
"""

from datetime import datetime, timezone
from typing import List, Optional

from app.contracts.nidhi_repository import INidhiRepository
from app.injector import injector
from app.models import (
    NidhiBalance,
    NidhiFundType,
    NidhiTransaction,
    NidhiTransactionStatus,
    NidhiTransactionType,
)


class ValidationError(Exception):
    """Input failed a business rule (bad amount, unknown fund, wrong
    approver, request already decided, insufficient balance, ...)."""


@injector
class NidhiDomain:
    def __init__(self, repo: INidhiRepository):
        self.repo = repo

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_balances(self, user_id: str) -> NidhiBalance:
        return self.repo.get_balances(user_id)

    def list_recent_transactions(self, limit: int = 10) -> List[NidhiTransaction]:
        return self.repo.list_transactions(limit=limit, archived=False)

    def list_archived_transactions(self, limit: int = 200) -> List[NidhiTransaction]:
        return self.repo.list_transactions(limit=limit, archived=True)

    def list_my_transactions(self, user_id: str, limit: int = 50) -> List[NidhiTransaction]:
        return self.repo.list_transactions_for_user(user_id, limit=limit, archived=False)

    def list_pending_contributions_for_user(self, user_id: str) -> List[NidhiTransaction]:
        """Only contributions offered TO this user -- they're the approver."""
        return [
            t for t in self.repo.list_pending()
            if t.type == NidhiTransactionType.CONTRIBUTION and t.user_id == user_id
        ]

    def list_pending_redemptions(self) -> List[NidhiTransaction]:
        """Every pending redemption, across all users -- admin-only view."""
        return [
            t for t in self.repo.list_pending()
            if t.type == NidhiTransactionType.REDEMPTION
        ]

    # ------------------------------------------------------------------
    # Contribute
    # ------------------------------------------------------------------

    def contribute(
        self,
        fund_type: NidhiFundType,
        amount: float,
        user_id: str,
        performed_by: str,
        note: Optional[str] = None,
    ) -> NidhiTransaction:
        """Creates a PENDING contribution. Money moves only once `user_id`
        (the recipient) approves it via approve_contribution()."""
        if amount is None or amount <= 0:
            raise ValueError("Contribution amount must be greater than 0.")
        if not float(amount).is_integer():
            raise ValueError("Contribution amount must be a whole unit.")
        if not user_id:
            raise ValueError("A user must be selected for this contribution.")

        return self.repo.add_transaction(
            NidhiTransaction(
                user_id=user_id,
                fund_type=fund_type,
                type=NidhiTransactionType.CONTRIBUTION,
                amount=amount,
                note=note,
                requested_by=performed_by,
                status=NidhiTransactionStatus.PENDING,
                created_at=datetime.now(timezone.utc),
            )
        )

    def approve_contribution(self, transaction_id: str, approved_by: str) -> NidhiTransaction:
        txn = self._require_pending(transaction_id, NidhiTransactionType.CONTRIBUTION)
        if approved_by != txn.user_id:
            raise ValidationError("Only the recipient of this contribution can approve it.")

        self.repo.adjust_balance(txn.requested_by, txn.fund_type, txn.amount)
        return self.repo.update_transaction(
            transaction_id,
            status=NidhiTransactionStatus.APPROVED,
            decided_by=approved_by,
            decided_at=datetime.now(timezone.utc),
        )

    def reject_contribution(
        self, transaction_id: str, rejected_by: str, reason: Optional[str] = None
    ) -> NidhiTransaction:
        txn = self._require_pending(transaction_id, NidhiTransactionType.CONTRIBUTION)
        if rejected_by != txn.user_id:
            raise ValidationError("Only the recipient of this contribution can reject it.")

        return self.repo.update_transaction(
            transaction_id,
            status=NidhiTransactionStatus.REJECTED,
            decided_by=rejected_by,
            decided_at=datetime.now(timezone.utc),
            decision_note=reason,
        )

    # ------------------------------------------------------------------
    # Redeem
    # ------------------------------------------------------------------

    def request_redeem(
        self,
        fund_type: NidhiFundType,
        amount: float,
        user_id: str,
        performed_by: str,
        note: Optional[str] = None,
    ) -> NidhiTransaction:
        if amount is None or amount <= 0:
            raise ValueError("Redemption amount must be greater than 0.")
        if not float(amount).is_integer():
            raise ValueError("Redemption amount must be a whole unit.")
        if not user_id:
            raise ValueError("A user must be selected for this redeem request.")

        balances = self.repo.get_balances(performed_by)
        available = balances.for_fund(fund_type)
        if amount > available:
            raise ValueError(
                f"Requested amount ({amount}) exceeds the requester's "
                f"available balance ({available})."
            )

        return self.repo.add_transaction(
            NidhiTransaction(
                user_id=user_id,
                fund_type=fund_type,
                type=NidhiTransactionType.REDEMPTION,
                amount=amount,
                note=note,
                requested_by=performed_by,
                status=NidhiTransactionStatus.PENDING,
                created_at=datetime.now(timezone.utc),
            )
        )

    def approve_redemption(
        self,
        transaction_id: str,
        approved_by: str,
        amount: Optional[float] = None,
        fund_type: Optional[NidhiFundType] = None,
        user_id: Optional[str] = None,
        tirtha_amount: Optional[float] = None,
        contribution_amount: Optional[float] = None,
    ) -> NidhiTransaction:
        """Admin-only (permission enforced at the router). `amount` /
        `fund_type` / `user_id` let the admin correct the request before
        approving it. Edits are written FIRST, as a separate update, so
        the balance check and the final `balance_after` stamp both use
        the corrected values rather than the originally submitted ones."""
        txn = self._require_pending(transaction_id, NidhiTransactionType.REDEMPTION)

        if tirtha_amount is not None or contribution_amount is not None:
            tirtha_amount = tirtha_amount or 0
            contribution_amount = contribution_amount or 0
            if tirtha_amount < 0 or contribution_amount < 0:
                raise ValidationError("Fund amounts cannot be negative.")
            if not float(tirtha_amount).is_integer() or not float(contribution_amount).is_integer():
                raise ValidationError("Fund amounts must be whole units.")
            if tirtha_amount <= 0 and contribution_amount <= 0:
                raise ValidationError("Enter an amount from at least one nidhi.")
            amount = tirtha_amount + contribution_amount
            if tirtha_amount > 0 and contribution_amount <= 0:
                fund_type = NidhiFundType.TIRTHA_NIDHI
            elif contribution_amount > 0 and tirtha_amount <= 0:
                fund_type = NidhiFundType.CONTRIBUTION_NIDHI

        edits = {}
        if amount is not None:
            if amount <= 0:
                raise ValidationError("Amount must be greater than 0.")
            if not float(amount).is_integer():
                raise ValidationError("Amount must be a whole unit.")
            edits["amount"] = amount
        if fund_type is not None:
            edits["fund_type"] = fund_type
        if user_id:
            edits["user_id"] = user_id
        if tirtha_amount is not None or contribution_amount is not None:
            edits["tirtha_amount"] = tirtha_amount or 0
            edits["contribution_amount"] = contribution_amount or 0
        if edits:
            txn = self.repo.update_transaction(transaction_id, **edits)

        balances = self.repo.get_balances(txn.requested_by)
        if tirtha_amount is not None and tirtha_amount > balances.tirtha_balance:
            raise ValidationError(
                f"Tirtha amount ({tirtha_amount}) exceeds {txn.requested_by}'s "
                f"available balance ({balances.tirtha_balance})."
            )
        if contribution_amount is not None and contribution_amount > balances.contribution_balance:
            raise ValidationError(
                f"Contribution amount ({contribution_amount}) exceeds {txn.requested_by}'s "
                f"available balance ({balances.contribution_balance})."
            )
        available = balances.for_fund(txn.fund_type)
        if tirtha_amount is None and contribution_amount is None and txn.amount > available:
            raise ValidationError(
                f"Cannot approve: amount ({txn.amount}) exceeds "
                f"{txn.requested_by}'s available balance ({available})."
            )

        if tirtha_amount is not None or contribution_amount is not None:
            if tirtha_amount:
                self.repo.adjust_balance(txn.requested_by, NidhiFundType.TIRTHA_NIDHI, -tirtha_amount)
            if contribution_amount:
                self.repo.adjust_balance(
                    txn.requested_by, NidhiFundType.CONTRIBUTION_NIDHI, -contribution_amount
                )
        else:
            self.repo.adjust_balance(txn.requested_by, txn.fund_type, -txn.amount)
        return self.repo.update_transaction(
            transaction_id,
            status=NidhiTransactionStatus.APPROVED,
            decided_by=approved_by,
            decided_at=datetime.now(timezone.utc),
        )

    def reject_redemption(
        self, transaction_id: str, rejected_by: str, reason: Optional[str] = None
    ) -> NidhiTransaction:
        self._require_pending(transaction_id, NidhiTransactionType.REDEMPTION)
        return self.repo.update_transaction(
            transaction_id,
            status=NidhiTransactionStatus.REJECTED,
            decided_by=rejected_by,
            decided_at=datetime.now(timezone.utc),
            decision_note=reason,
        )

    # ------------------------------------------------------------------
    # Shared helper
    # ------------------------------------------------------------------

    def _require_pending(
        self, transaction_id: str, expected_type: NidhiTransactionType
    ) -> NidhiTransaction:
        txn = self.repo.get_transaction(transaction_id)
        if not txn:
            raise ValidationError(f"Nidhi request '{transaction_id}' not found.")
        if txn.type != expected_type:
            raise ValidationError(f"This request is not a {expected_type.value}.")
        if txn.status != NidhiTransactionStatus.PENDING:
            raise ValidationError(f"Nidhi request '{transaction_id}' has already been decided.")
        return txn