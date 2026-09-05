"""
Controller for the Nidhi (fund) domain -- same role as
`app/controllers/books_controller.py`: routers hand this plain,
already-parsed values and get back plain data or a domain exception.
"""

from typing import List, Optional

from app.domain import nidhi_domain as nd
from app.models import NidhiBalance, NidhiFundType, NidhiTransaction


class NidhiController:
    def __init__(self, domain: Optional[nd.NidhiDomain] = None):
        self.domain = domain if domain is not None else nd.NidhiDomain()

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_balances(self, user_id: str) -> NidhiBalance:
        return self.domain.get_balances(user_id)

    def list_recent_transactions(self, limit: int = 10) -> List[NidhiTransaction]:
        return self.domain.list_recent_transactions(limit=limit)

    def list_archived_transactions(self, limit: int = 200) -> List[NidhiTransaction]:
        return self.domain.list_archived_transactions(limit=limit)

    def list_my_transactions(self, user_id: str, limit: int = 50) -> List[NidhiTransaction]:
        return self.domain.list_my_transactions(user_id, limit=limit)

    def list_pending_contributions_for_user(self, user_id: str) -> List[NidhiTransaction]:
        return self.domain.list_pending_contributions_for_user(user_id)

    def list_pending_redemptions(self) -> List[NidhiTransaction]:
        return self.domain.list_pending_redemptions()

    def dashboard_data(self, user_id: str) -> dict:
        """This user's balances + recent activity + THEIR OWN pending
        contribution decisions. Redemption review is a separate,
        permission-gated call (list_pending_redemptions) -- it isn't
        folded in here since not every caller of /dashboard is an admin."""
        my_pending = self.domain.list_pending_contributions_for_user(user_id)
        return {
            "balances": self.domain.get_balances(user_id),
            "recent_transactions": self.domain.list_recent_transactions(limit=10),
            "my_pending_contributions": my_pending,
            "my_pending_count": len(my_pending),
        }

    # ------------------------------------------------------------------
    # Commands -- contribute
    # ------------------------------------------------------------------

    def contribute(
        self,
        fund_type: NidhiFundType,
        amount: float,
        user_id: str,
        performed_by: str,
        note: Optional[str] = None,
    ) -> NidhiTransaction:
        return self.domain.contribute(fund_type, amount, user_id, performed_by, note)

    def approve_contribution(self, transaction_id: str, approved_by: str) -> NidhiTransaction:
        return self.domain.approve_contribution(transaction_id, approved_by)

    def reject_contribution(
        self, transaction_id: str, rejected_by: str, reason: Optional[str] = None
    ) -> NidhiTransaction:
        return self.domain.reject_contribution(transaction_id, rejected_by, reason)

    # ------------------------------------------------------------------
    # Commands -- redeem
    # ------------------------------------------------------------------

    def request_redeem(
        self,
        fund_type: NidhiFundType,
        amount: float,
        user_id: str,
        performed_by: str,
        note: Optional[str] = None,
    ) -> NidhiTransaction:
        return self.domain.request_redeem(fund_type, amount, user_id, performed_by, note)

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
        return self.domain.approve_redemption(
            transaction_id,
            approved_by,
            amount=amount,
            fund_type=fund_type,
            user_id=user_id,
            tirtha_amount=tirtha_amount,
            contribution_amount=contribution_amount,
        )

    def reject_redemption(
        self, transaction_id: str, rejected_by: str, reason: Optional[str] = None
    ) -> NidhiTransaction:
        return self.domain.reject_redemption(transaction_id, rejected_by, reason)