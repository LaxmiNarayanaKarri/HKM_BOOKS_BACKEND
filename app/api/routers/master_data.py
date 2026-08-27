from fastapi import APIRouter, Depends

from app.api.deps import get_books_controller, get_master_data_controller
from app.controllers.master_data import MasterDataController
from app.core.auth import CurrentUser, get_current_user
from app.models import BookCreate, NameCreate, ThresholdUpdate
from app.controllers.books_controller import BooksController

router = APIRouter(prefix="/api/master-data", tags=["master-data"])


@router.get("", summary="Catalog / categories / languages / locations / events")
def get_master_data(
    user: CurrentUser = Depends(get_current_user),
    controller: MasterDataController = Depends( get_master_data_controller),
):
    return controller.get_master_data()


@router.post("/books", summary="Add a book to the catalog", status_code=201)
def add_book(
    payload: BookCreate,
    user: CurrentUser = Depends(get_current_user),
    controller: MasterDataController = Depends(get_master_data_controller),
):
    book, created = controller.add_book(
        title=payload.title,
        short_title=payload.short_title,
        threshold=payload.threshold,
        category=payload.category,
        language=payload.language
    )
    message = (
        f'Added "{book.title}" ({book.short_title or "no shorthand"}) to the catalog.'
        if created else f'"{book.title}" is already in the catalog.'
    )
    return {"message": message, "book": book, "created": created}

@router.post("/books/threshold", summary="Update a book's low-stock threshold")
def update_threshold(
    payload: ThresholdUpdate,
    user: CurrentUser = Depends(get_current_user),
    controller: MasterDataController = Depends(get_master_data_controller),
):
    book = controller.update_book_threshold(
        title=payload.title,
        threshold=payload.threshold
    )
    return {"message": f'Threshold for "{payload.title}" set to {payload.threshold}.', "book": book}


@router.post("/categories", summary="Add a category", status_code=201)
def add_category(
    payload: NameCreate,
    user: CurrentUser = Depends(get_current_user),
    controller: MasterDataController = Depends(get_master_data_controller),
):
    name = controller.add_category(payload.name)
    return {"message": f'Added category "{payload.name}".', "name": payload.name}


@router.post("/languages", summary="Add a language", status_code=201)
def add_language(
    payload: NameCreate,
    user: CurrentUser = Depends(get_current_user),
    controller: MasterDataController = Depends(get_master_data_controller),
):
    name = controller.add_language(payload.name)
    return {"message": f'Added language "{payload.name}".', "name": payload.name}


@router.post("/locations", summary="Add a location", status_code=201)
def add_location(
    payload: NameCreate,
    user: CurrentUser = Depends(get_current_user),
    controller: MasterDataController = Depends(get_master_data_controller),
):
    name = controller.add_location(payload.name)
    return {"message": f'Added location "{payload.name}".', "name": payload.name}

@router.get("/locations", summary="List all locations")
def list_locations(
    user: CurrentUser = Depends(get_current_user),
    controller: MasterDataController = Depends(get_master_data_controller),
):
    locations = controller.list_locations()
    return {"locations": locations}

@router.post("/sources", summary="Add a source", status_code=201)
def add_source(
    payload: NameCreate,
    user: CurrentUser = Depends(get_current_user),
    controller: MasterDataController = Depends(get_master_data_controller),
):
    name = controller.add_source(payload.name)
    return {"message": f'Added source "{payload.name}".', "name": payload.name}

@router.get("/sources", summary="List all sources")
def list_sources(
    user: CurrentUser = Depends(get_current_user),
    controller: MasterDataController = Depends(get_master_data_controller),
):
    sources = controller.list_sources()
    return {"sources": sources}


@router.post("/events", summary="Add an event", status_code=201)
def add_event(
    payload: NameCreate,
    user: CurrentUser = Depends(get_current_user),
    controller: MasterDataController = Depends(get_master_data_controller),
):
    name = controller.add_event(payload.name)
    return {"message": f'Added event "{payload.name}".', "name": payload.name}  
