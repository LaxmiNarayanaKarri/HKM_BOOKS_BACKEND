"""
Local dev entrypoint for the Books service.

Location: books/run.py  (same folder as requirements.txt / Dockerfile,
one level above the `app` package)

Usage:
    cd books
    pip install -r requirements.txt
    python run.py

Runs on http://localhost:8001 by default. Catalog endpoints
(GET /books, /books/{id}) need real SUPABASE_URL / SUPABASE_KEY env
vars to work; everything else (dashboard, sell, inward-stock,
master-data, backup) runs fine against the built-in in-memory store
without any extra setup.

Env vars:
    HOST             default 0.0.0.0
    PORT             default 8001
    RELOAD           default true (auto-restart on code changes)
    SUPABASE_URL     only needed for the /books catalog endpoints
    SUPABASE_KEY     only needed for the /books catalog endpoints
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 8001)),
        reload=os.environ.get("RELOAD", "true").lower() == "true",
    )