from fastapi import APIRouter, Depends, Request

from app.api.deps import get_books_controller
from app.controllers.books_controller import BooksController
from app.core.auth import CurrentUser, get_current_user, require_admin
from app.core.xlsx_export import send_xlsx

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", summary="Personal (or org-wide) overview + inventory")
def get_dashboard(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    controller: BooksController = Depends(get_books_controller),
):
    return controller.dashboard_data(user.username, user.is_admin, request.query_params)


@router.get("/export/leaderboard", summary="Top Distributors table as .xlsx (admin only)")
def export_leaderboard(
    request: Request,
    user: CurrentUser = Depends(require_admin),
    controller: BooksController = Depends(get_books_controller),
):
    rows, f = controller.leaderboard_export_rows(user.username, request.query_params)
    return send_xlsx(
        rows, columns=["seller", "revenue", "qty", "profit"],
        headers=["Name", "Amount Collected", "Qty", "Profit"],
        sheet_name="Top Distributors",
        filename=f"top_distributors_{f.date_from}_to_{f.date_to}.xlsx",
    )


@router.get("/export/top-books", summary="Top Books table as .xlsx")
def export_top_books(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    controller: BooksController = Depends(get_books_controller),
):
    rows, f = controller.top_books_export_rows(user.username, user.is_admin, request.query_params)
    return send_xlsx(
        rows, columns=["title", "qty"], headers=["Title", "Qty Distributed"],
        sheet_name="Top Books", filename=f"top_books_{f.date_from}_to_{f.date_to}.xlsx",
    )


@router.get("/export/inventory", summary="Book Inventory table as .xlsx")
def export_inventory(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    controller: BooksController = Depends(get_books_controller),
):
    rows, f = controller.inventory_export_rows(user.username, user.is_admin, request.query_params)
    return send_xlsx(
        rows,
        columns=["title", "available", "threshold", "avg_cost", "avg_sell", "profit_or_loss", "pl_pct"],
        headers=["Book Name", "Stock in Hand (Available)", "Threshold", "Avg Cost / Book",
                 "Avg Sell / Book", "Profit or Loss", "% Profit/Loss"],
        sheet_name="Book Inventory", filename=f"book_inventory_{f.date_from}_to_{f.date_to}.xlsx",
    )
