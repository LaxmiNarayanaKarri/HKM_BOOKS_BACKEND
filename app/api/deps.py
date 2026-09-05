"""
Shared FastAPI dependencies for the Books routers -- one place that
builds a `BooksController` per request, so every router pulls its
controller the same way instead of constructing `BooksController()`
inline.
"""

from app.controllers.books_controller import BooksController
from app.controllers.master_data import MasterDataController
from app.controllers.purchases_controller import PurchasesController
from app.controllers.sales_controller import SalesController
from app.controllers.nidhi_controller import NidhiController
from app.controllers.book_requests_controller import BookRequestsController


def get_books_controller() -> BooksController:
    return BooksController()

def get_master_data_controller() -> MasterDataController:
    return MasterDataController()    

def get_purchases_controller() -> PurchasesController:
    return PurchasesController()

def get_sales_controller() -> SalesController:
    return SalesController()

def get_nidhi_controller() -> NidhiController:
    return NidhiController()

def get_book_requests_controller() -> BookRequestsController:
    return BookRequestsController()