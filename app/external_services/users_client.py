# app/external_services/users_client.py
import os
from typing import Optional
from .base_client import BaseServiceClient


class UsersClient(BaseServiceClient):
    """
    Books Pod client for calling internal Users Pod routes.
    All requests are automatically authenticated via X-Internal-Token.
    """

    def __init__(self) -> None:
        super().__init__(base_url=os.environ.get("USERS_SERVICE_BASE_URL", ""))

    async def get_user_by_id(self, user_id: int) -> Optional[dict]:
        response = await self.get(f"/internal/users/{user_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def get_all_volunteers(self) -> list[dict]:
        response = await self.get("/internal/volunteers")
        response.raise_for_status()
        return response.json()

    async def get_volunteer_by_id(self, volunteer_id: int) -> Optional[dict]:
        response = await self.get(f"/internal/volunteers/{volunteer_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def verify_user_exists(self, user_id: int) -> bool:
        user = await self.get_user_by_id(user_id)
        return user is not None