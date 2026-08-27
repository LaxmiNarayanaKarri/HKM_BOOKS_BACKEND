"""
Thin client for the Users service.

Replaces the old `from backend.users.domain import get_user` in-process
import, which only worked when Books and Users shared a Python process.
Books is deployed as its own isolated pod now (see `k8s-deployment.yaml`),
so this needs to become a real HTTP call to the Users service -- the
same idea as the reverse direction described in that service's own
`app.py` (Users calling Books over HTTP via a `books_client.py`).

Fill in `USERS_SERVICE_URL` and the request below when this is wired up
for real; until then this returns `None`, which every caller already
handles the same way a "no such user" result did before.
"""

import os
from dataclasses import dataclass
from typing import Optional

USERS_SERVICE_URL = os.environ.get("USERS_SERVICE_URL", "")


@dataclass
class UserInfo:
    username: str
    name: str
    role: str = "user"


def get_user(username: str) -> Optional[UserInfo]:
    if not username or not USERS_SERVICE_URL:
        return None
    # TODO: replace with a real call once the Users service exposes an
    # internal endpoint for this, e.g.:
    #
    #   import httpx
    #   resp = httpx.get(f"{USERS_SERVICE_URL}/internal/users/{username}", timeout=3)
    #   if resp.status_code == 200:
    #       data = resp.json()
    #       return UserInfo(username=data["username"], name=data["name"], role=data.get("role", "user"))
    return None
