"""
`app/infra/vercel_blob_store.py`

`IBlobStore` implementation backed by Vercel Blob.

There's no official Vercel Blob SDK for Python (only Node/Edge), so
this talks to the underlying HTTP API directly with `httpx`, the same
API the `@vercel/blob` JS SDK itself calls. That means these header
names (`x-api-version`, `x-add-random-suffix`, `x-allow-overwrite`)
are inferred from the published SDK behavior rather than a documented
Python contract -- if Vercel changes the wire protocol, this is the
one file that needs updating. Worth a smoke test against a real Blob
store before relying on it in production.

Auth: reads BLOB_READ_WRITE_TOKEN from the environment, same variable
`vercel env pull` gives you locally and Vercel injects automatically
in deployments.

Deterministic paths: by default Vercel Blob appends a random suffix
to every upload (so two `put()`s never collide) and refuses to
overwrite an existing pathname. We want the opposite here -- the
whole point of `/transactions/{user_id}/{transaction_id}.json` is a
predictable, re-fetchable address -- so every write disables the
suffix and allows overwrite.
"""

import json
import os
from typing import Any, Dict, List, Optional

import httpx

from app.contracts.blob_storage_contact import IBlobStore
from app.injector import singleton

BLOB_API_BASE = "https://blob.vercel-storage.com"


@singleton(IBlobStore)
class VercelBlobStore(IBlobStore):
    def __init__(self, token: Optional[str] = None, client: Optional[httpx.Client] = None):
        self.token = token or os.environ["BLOB_READ_WRITE_TOKEN"]
        self._client = client or httpx.Client(timeout=15.0)

    def _headers(self, **extra: str) -> Dict[str, str]:
        return {
            "authorization": f"Bearer {self.token}",
            "x-api-version": "7",
            **extra,
        }

    # -- IBlobStore ---------------------------------------------------
    def put_json(self, path: str, data: Dict[str, Any]) -> str:
        body = json.dumps(data, default=str).encode("utf-8")
        resp = self._client.put(
            f"{BLOB_API_BASE}/{path}",
            content=body,
            headers=self._headers(
                **{
                    "content-type": "application/json",
                    "x-add-random-suffix": "0",
                    "x-allow-overwrite": "1",
                }
            ),
        )
        resp.raise_for_status()
        return resp.json()["url"]

    def get_json(self, path: str) -> Optional[Dict[str, Any]]:
        # Blobs are served publicly off their CDN URL rather than
        # through the management API, so we resolve the pathname to a
        # URL via `head`-style lookup (list with an exact prefix, one
        # result expected) and fetch that.
        matches = self._list_raw(prefix=path)
        exact = next((b for b in matches if b["pathname"] == path), None)
        if exact is None:
            return None
        resp = self._client.get(exact["url"])
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def list_paths(self, prefix: str) -> List[str]:
        return [b["pathname"] for b in self._list_raw(prefix=prefix)]

    def delete(self, path: str) -> None:
        resp = self._client.request(
            "DELETE",
            BLOB_API_BASE,
            headers=self._headers(**{"content-type": "application/json"}),
            content=json.dumps({"urls": [f"{BLOB_API_BASE}/{path}"]}),
        )
        resp.raise_for_status()

    # -- internal helpers -------------------------------------------------
    def _list_raw(self, prefix: str) -> List[Dict[str, Any]]:
        blobs: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        while True:
            params: Dict[str, str] = {"prefix": prefix, "limit": "1000"}
            if cursor:
                params["cursor"] = cursor
            resp = self._client.get(BLOB_API_BASE, params=params, headers=self._headers())
            resp.raise_for_status()
            page = resp.json()
            blobs.extend(page.get("blobs", []))
            if not page.get("hasMore"):
                break
            cursor = page.get("cursor")
        return blobs