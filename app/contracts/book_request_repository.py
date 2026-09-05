from abc import ABC, abstractmethod
from typing import List, Optional

from app.models import BookRequest


class IBookRequestRepository(ABC):
    @abstractmethod
    def create(self, request: BookRequest) -> BookRequest:
        raise NotImplementedError

    @abstractmethod
    def list_for_user(self, username: str, limit: int = 200) -> List[BookRequest]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self, limit: int = 500) -> List[BookRequest]:
        raise NotImplementedError

    @abstractmethod
    def update_status(self, request_id: str, status: str) -> Optional[BookRequest]:
        raise NotImplementedError
