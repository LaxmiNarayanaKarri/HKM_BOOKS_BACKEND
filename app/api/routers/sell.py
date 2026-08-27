from fastapi import APIRouter, Depends, Query

from app.api.deps import get_sales_controller
from app.controllers.sales_controller import SalesController
from app.core.auth import CurrentUser, get_current_user
from app.core.xlsx_export import send_xlsx
from app.models import SaleCreate

router = APIRouter(prefix="/api/sell", tags=["sell"])


@router.get("", summary="Sell-entry form data + recent entries")
def get_sell_entry_page(
    se_user: str = Query(default="all"),
    se_event: str = Query(default="all"),
    se_date_from: str = Query(default=""),
    se_date_to: str = Query(default=""),
    se_location: str = Query(default="all"),
    user: CurrentUser = Depends(get_current_user),
    controller: SalesController = Depends(get_sales_controller),
):
    return controller.sell_entry_page_data(
        user.username, se_user, se_event, se_date_from, se_date_to, se_location
    )


@router.post("", summary="Record a sale", status_code=201)
def create_sell_entry(
    payload: SaleCreate,
    user: CurrentUser = Depends(get_current_user),
    controller: SalesController = Depends(get_sales_controller),
):
    row = controller.record_sell_entry(user.username, payload)
    return {"message": f'Recorded sale of {row.qty} x "{row.title}".', "sale": row}


@router.get("/export", summary="My Recent Entries table as .xlsx")
def export_sell_entries(
    se_user: str = Query(default="all"),
    se_event: str = Query(default="all"),
    se_date_from: str = Query(default=""),
    se_date_to: str = Query(default=""),
    user: CurrentUser = Depends(get_current_user),
    controller: SalesController = Depends(get_sales_controller),
):
    rows = controller.export_sell_entries_rows(
        user.username, se_user, se_event, se_date_from, se_date_to
    )
    # Fixed: "location" was listed twice in `columns` (with headers
    # "Event" then "Location" for the same underlying field) -- there is
    # only one location/event value per sale row, so this now exports a
    # single "Event" column instead of a duplicated one.
    return send_xlsx(
        rows, columns=["date", "title", "location", "qty", "sell_price"],
        headers=["Distribution Date", "Book Name", "Event", "Qty", "Sell Price"],
        sheet_name="My Recent Entries", filename=f"my_sales_{user.username}.xlsx",
    )