from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import get_nidhi_controller
from app.controllers.nidhi_controller import NidhiController
from app.core.auth import CurrentUser, require_permission
from app.models import NidhiFundType, RedemptionDecisionRequest

router = APIRouter(prefix="/nidhi", tags=["nidhi"])


# ------------------------------------------------------------------
# Request bodies -- thin DTOs, kept next to the router the same way
# other simple POST payloads are in this codebase. The router unpacks
# these into plain args before calling the controller, so the
# controller/domain never depend on a FastAPI/pydantic type.
# ------------------------------------------------------------------

class ContributeRequest(BaseModel):
    # FIX: was missing -- without this the router had no way to know
    # WHO the contribution is for, and fell back to using the caller's
    # own identity as the recipient.
    user_id: str
    fund_type: NidhiFundType
    amount: float
    note: Optional[str] = None


class RedeemRequest(BaseModel):
    # FIX: same as ContributeRequest above.
    user_id: str
    fund_type: NidhiFundType
    amount: float
    note: Optional[str] = None


# NOTE: RejectRequest was removed -- every reject/approve decision now
# uses RedemptionDecisionRequest (imported from app.models) instead,
# including for contributions, so there's one shared shape.


# ------------------------------------------------------------------
# Reads
# ------------------------------------------------------------------

@router.get("/dashboard", summary="Balances, recent activity, and my pending contributions")
def get_dashboard(
    user: CurrentUser = Depends(require_permission("nidhi")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    return controller.dashboard_data(user.username)


@router.get("/balances", summary="Current user's balance of both funds")
def get_balances(
    user: CurrentUser = Depends(require_permission("nidhi")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    return controller.get_balances(user.username)


@router.get("/balances/{user_id}", summary="A user's balance of both funds")
def get_user_balances(
    user_id: str,
    user: CurrentUser = Depends(require_permission("nidhi")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    return controller.get_balances(user_id)


@router.get("/transactions", summary="Recent (or archived) transactions, admin only")
def get_transactions(
    limit: int = Query(default=10, ge=1, le=500),
    archived: bool = Query(default=False),
    user: CurrentUser = Depends(require_permission("nidhi_approve")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    if archived:
        return controller.list_archived_transactions(limit=limit)
    return controller.list_recent_transactions(limit=limit)


@router.get("/transactions/mine", summary="The current user's own transactions")
def get_my_transactions(
    limit: int = Query(default=50, ge=1, le=500),
    user: CurrentUser = Depends(require_permission("nidhi")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    return controller.list_my_transactions(user.username, limit=limit)


# NOTE: the old unified `GET /approvals/pending`, `POST
# /approvals/{id}/approve`, and `POST /approvals/{id}/reject` routes were
# removed here -- they called controller.list_pending_requests() /
# approve_request() / reject_request(), none of which exist anymore now
# that approval is split by transaction type. They're fully replaced by
# the /contributions/... and /redemptions/... routes below.


# ------------------------------------------------------------------
# Commands -- contribute
# ------------------------------------------------------------------

@router.post("/contribute", summary="Raise a pending contribution for a user to approve")
def contribute(
    payload: ContributeRequest,
    user: CurrentUser = Depends(require_permission("nidhi")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    # ValueError (bad amount, ...) propagates to the app-wide handler
    # in app/core/errors.py and becomes a 400.
    return controller.contribute(
        fund_type=payload.fund_type,
        amount=payload.amount,
        user_id=payload.user_id,
        performed_by=user.username,
        note=payload.note,
    )


@router.get("/contributions/pending/mine", summary="Contributions offered to me, awaiting my decision")
def get_my_pending_contributions(
    user: CurrentUser = Depends(require_permission("nidhi")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    return controller.list_pending_contributions_for_user(user.username)


@router.post("/contributions/{transaction_id}/approve", summary="Approve a contribution offered to me")
def approve_contribution(
    transaction_id: str,
    user: CurrentUser = Depends(require_permission("nidhi")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    # ValidationError (not yours to approve, already decided, ...) -> 400
    return controller.approve_contribution(transaction_id, approved_by=user.username)


@router.post("/contributions/{transaction_id}/reject", summary="Reject a contribution offered to me")
def reject_contribution(
    transaction_id: str,
    payload: RedemptionDecisionRequest,
    user: CurrentUser = Depends(require_permission("nidhi")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    return controller.reject_contribution(
        transaction_id, rejected_by=user.username, reason=payload.reason
    )


# ------------------------------------------------------------------
# Commands -- redeem
# ------------------------------------------------------------------

@router.post("/redeem", summary="Request a redemption from a fund (goes to admin review)")
def redeem(
    payload: RedeemRequest,
    user: CurrentUser = Depends(require_permission("nidhi")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    return controller.request_redeem(
        fund_type=payload.fund_type,
        amount=payload.amount,
        user_id=payload.user_id,
        performed_by=user.username,
        note=payload.note,
    )


@router.get("/redemptions/pending", summary="Every pending redemption, awaiting admin review")
def get_pending_redemptions(
    user: CurrentUser = Depends(require_permission("nidhi_approve")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    return controller.list_pending_redemptions()


@router.post("/redemptions/{transaction_id}/approve", summary="Approve a redemption with reviewed fund amount")
def approve_redemption(
    transaction_id: str,
    payload: RedemptionDecisionRequest,
    user: CurrentUser = Depends(require_permission("nidhi_approve")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    return controller.approve_redemption(
        transaction_id,
        approved_by=user.username,
        tirtha_amount=payload.tirtha_amount,
        contribution_amount=payload.contribution_amount,
    )


@router.post("/redemptions/{transaction_id}/reject", summary="Reject a pending redemption")
def reject_redemption(
    transaction_id: str,
    payload: RedemptionDecisionRequest,
    user: CurrentUser = Depends(require_permission("nidhi_approve")),
    controller: NidhiController = Depends(get_nidhi_controller),
):
    return controller.reject_redemption(
        transaction_id, rejected_by=user.username, reason=payload.reason
    )