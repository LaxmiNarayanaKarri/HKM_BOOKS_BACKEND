from fastapi import APIRouter, HTTPException

from app.controllers.books_controller import BooksController

router = APIRouter(tags=["catalog"])


@router.get("/books", summary="Get all books")
def get_books():
    return BooksController().list_books()


@router.get("/books/{book_id}", summary="Get book by ID")
def get_book_by_id(book_id: int):
    book = BooksController().get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.get("/health", summary="Health check")
def health_check():
    return {"status": "healthy", "pod": "isolated-books-api", "version": "2.0.0"}