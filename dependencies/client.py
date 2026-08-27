from functools import lru_cache
from backend.books.app.external_services.users_client import UsersClient

@lru_cache(maxsize=1)
def get_users_client() -> UsersClient:
    return UsersClient()