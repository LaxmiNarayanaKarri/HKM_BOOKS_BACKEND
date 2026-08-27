from fastapi import APIRouter, Depends

from app.api.deps import get_books_controller
from app.controllers.books_controller import BooksController
from app.core.auth import CurrentUser, get_current_user
from app.core.xlsx_export import send_xlsx_multi

router = APIRouter(prefix="/api/backup", tags=["backup"])

SALES_BACKUP_COLUMNS = ["date", "title", "category", "seller", "qty", "cost_price", "sell_price", "language", "location"]
PURCHASES_BACKUP_COLUMNS = ["date", "title", "short_title", "category", "language", "source", "qty", "cost_price", "recorded_by"]


@router.get("", summary="Last-7-days backup availability, one entry per day")
def get_backup_days(
    user: CurrentUser = Depends(get_current_user),
    controller: BooksController = Depends(get_books_controller),
):
    return controller.backup_page_data()


@router.get("/download/{day}", summary="Download that single day's backup as .xlsx")
def download_backup(
    day: str,
    user: CurrentUser = Depends(get_current_user),
    controller: BooksController = Depends(get_books_controller),
):
    # ValidationError (out-of-range day) propagates to the app-wide
    # handler in app/core/errors.py and becomes a 400.
    sales_rows, purchase_rows = controller.backup_download_rows(day)
    return send_xlsx_multi(
        [
            ("Sales", sales_rows, SALES_BACKUP_COLUMNS, None),
            ("Inward Stock", purchase_rows, PURCHASES_BACKUP_COLUMNS, None),
        ],
        filename=f"fnrg_backup_{day}.xlsx",
    )
