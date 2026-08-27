# """
# Internal, service-to-service endpoints -- the HTTP equivalent of the
# in-process calls the Users service used to make straight into
# `books.controllers.get_locations()` / `location_overview_data()` when
# Users and Books shared one process (e.g. for Users' Volunteer
# Assignment / Locations Overview page). Not meant for browser/frontend
# clients; only for the Users service (or an API gateway) to call.

# In a real deployment this would normally sit behind network policy /
# an internal-only ingress rather than auth headers alone -- left as a
# TODO alongside the rest of the auth wiring in app/core/auth.py.
# """

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.params import Query
from app.api.deps import get_master_data_controller, get_sales_controller
from app.controllers.master_data import MasterDataController
from app.controllers.sales_controller import SalesController
from dependencies.auth import verify_internal_token

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(verify_internal_token)],
)


@router.get("/locations", summary="[internal] All known locations")
def get_locations(controller: MasterDataController = Depends(get_master_data_controller)):
    return {"locations": controller.list_locations()}

@router.get("/location-overview", summary="[internal] Sales totals for one date/location")
def get_location_overview(
    ov_date_from: str = Query(default=""),
    ov_date: str = Query(default=""),
    ov_location: str = Query(default="all"),
    ov_event: str = Query(default="all"),
    controller: SalesController = Depends(get_sales_controller),
):
    return controller.get_location_overview(ov_date_from, ov_date, ov_location, ov_event)


@router.get("/events", summary="[internal] All known events")
def get_events(controller: MasterDataController = Depends(get_master_data_controller)):
    return {"events": controller.list_events()}
