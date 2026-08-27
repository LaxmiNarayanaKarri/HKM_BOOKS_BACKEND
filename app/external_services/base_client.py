# external_services/base_client.py
import os
import httpx


class BaseServiceClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "X-Internal-Token": os.environ.get("INTERNAL_SERVICE_TOKEN", ""),
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=10.0,
        )

    async def get(self, path: str, params: dict = None) -> httpx.Response:
        async with self._client() as client:
            return await client.get(path, params=params)

    async def post(self, path: str, json: dict = None) -> httpx.Response:
        async with self._client() as client:
            return await client.post(path, json=json)

    async def put(self, path: str, json: dict = None) -> httpx.Response:
        async with self._client() as client:
            return await client.put(path, json=json)

    async def delete(self, path: str, json: dict = None) -> httpx.Response:
        async with self._client() as client:
            return await client.delete(path, content=json)