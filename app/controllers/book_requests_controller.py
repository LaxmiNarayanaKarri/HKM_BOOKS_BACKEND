from typing import List

from app.contracts.book_request_repository import IBookRequestRepository
from app.injector import injector
from app.models import BookRequest


@injector
class BookRequestsController:
    def __init__(self, repo: IBookRequestRepository):
        self.repo = repo

    def create(self, request: BookRequest) -> BookRequest:
        return self.repo.create(request)

    def list_for_user(self, username: str) -> List[BookRequest]:
        return self.repo.list_for_user(username)

    def list_all(self) -> List[BookRequest]:
        return self.repo.list_all()

    def approve(self, request_id: str) -> BookRequest:
        request = self.repo.update_status(request_id, "fulfilled")
        if not request:
            raise ValueError("Book request not found.")
        return request
