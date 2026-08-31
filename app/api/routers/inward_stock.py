from fastapi import APIRouter, Depends, Request

from app.api.deps import get_books_controller, get_purchases_controller
from app.controllers.purchases_controller import PurchasesController
from app.core.auth import CurrentUser, require_permission
from app.core.xlsx_export import send_xlsx
from app.models import PurchaseBatchCreate

router = APIRouter(prefix="/api/inward-stock", tags=["inward-stock"])


@router.get("", summary="Inward-stock form data + recent purchases")
def get_inward_stock_page(
    request: Request,
    user: CurrentUser = Depends(require_permission("inward_stock_write")),
    controller: PurchasesController = Depends(get_purchases_controller),
):
    return controller.inward_stock_page_data(request.query_params)


@router.post("", summary="Record a batch of received stock", status_code=201)
def create_inward_stock(
    payload: PurchaseBatchCreate,
    user: CurrentUser = Depends(require_permission("inward_stock_write")),
    controller: PurchasesController = Depends(get_purchases_controller),
):
    print(f"Received payload: {payload}", user)
    added = controller.record_inward_stock(user.username, payload)
    if added:
        return {
            "message": f"Recorded {added} book{'s' if added != 1 else ''} received into stock.",
            "added": added,
        }
    return {
        "message": "No valid rows to record — check titles, quantities and required fields.",
        "added": 0,
    }


@router.get("/export", summary="Recent Purchases table as .xlsx")
def export_inward_stock(
    request: Request,
    user: CurrentUser = Depends(require_permission("inward_stock_write")),
    controller: PurchasesController = Depends(get_purchases_controller),
):
    rows = controller.export_inward_stock_rows(request.query_params)
    return send_xlsx(
        rows,
        columns=["date", "title", "short_title", "category", "language", "source", "qty", "cost_price", "total_cost", "recorded_by"],
        headers=["Purchase Date", "Book Title", "Short Title", "Category", "Language", "Source", "Qty", "Cost/Unit", "Total Cost", "Recorded By"],
        sheet_name="Recent Purchases", filename="inward_stock.xlsx",
    )
