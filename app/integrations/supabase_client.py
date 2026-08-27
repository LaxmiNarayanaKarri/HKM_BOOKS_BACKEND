"""
Supabase resource -- the concrete implementation of `DBContract`
(see `app/injector.py`).

This is the ONE place that knows how to reach the database. It builds
a `supabase-py` client from environment variables and hands it out via
`get_client()`. Anything that needs DB access (right now, just
`SupabaseUserRepository`) asks for `DBContract` in its constructor and
gets *this* singleton auto-injected -- see `app/injector.py`'s
`@injector` / `@singleton` decorators.

Required environment variables
-------------------------------
    SUPABASE_URL   -- e.g. https://xxxxxxxx.supabase.co
    SUPABASE_KEY   -- service_role key (server-side; bypasses RLS) or
                       an anon key + matching RLS policies on `users`

Load them however you like (real env vars, a process manager, ...).
For local dev, `python-dotenv` is wired up in `main.py`, so a `.env`
file at the project root (see `.env.example`) works too.
"""

import os
from typing import Optional

from supabase import Client, create_client

from app.injector import DBContract, singleton
from dotenv import load_dotenv
load_dotenv()  # load .env for local dev (see .env.example)

@singleton(DBContract)
class SupabaseDB(DBContract):
    """Lazy, singleton Supabase client. `connect()` is idempotent and
    is also called automatically by `get_client()` the first time
    anything actually needs the client, so nothing has to remember to
    call it explicitly at startup."""

    def __init__(self):
        self._client: Optional[Client] = None

    def connect(self) -> None:
        if self._client is not None:
            return

        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_KEY", "").strip()
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in the environment "
                "before the Users service can talk to the database. See "
                ".env.example."
            )
        self._client = create_client(url, key)

    def disconnect(self) -> None:
        # supabase-py's Client has no explicit close(); dropping the
        # reference is enough to let the underlying HTTP connections
        # be garbage-collected. Kept as an explicit method so callers
        # (e.g. test teardown) have a clean hook.
        self._client = None

    def get_client(self) -> Client:
        if self._client is None:
            self.connect()
        return self._client
