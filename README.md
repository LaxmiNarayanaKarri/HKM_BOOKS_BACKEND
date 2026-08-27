# Isolated Books API (v2) - Contract & Injection Architecture

A pure-backend (JSON only, no templates/sessions) FastAPI service for
the Books domain: catalog, sell entries, inward stock, dashboard
analytics, backups, and master data.

## Architecture

- `app/contracts/` -- abstract interfaces (`IBookRepository`, and
  `DBContract`/`FileStorageContract` in `app/injector.py`).
- `app/db/` -- data-access resources: `supabase_client.py` (the
  Supabase-backed singleton used by the catalog service below) and
  `db.py` (an in-memory reference store used by the business-logic
  domain layer -- see note below).
- `app/repositories/`, `app/storage/` -- concrete implementations of
  the contracts above (`SupabaseBookRepository`, `SupabaseFileStorage`).
- `app/domain/` -- framework-free business logic:
  - `book_service.py` -- thin catalog reads via `IBookRepository`.
  - `books_domain.py` -- sales/inventory/purchases business rules and
    analytics (`BooksDomain`).
- `app/controllers/books_controller.py` -- glue layer between routers
  and the domain: assembles response payloads, never renders anything
  or touches a request object directly.
- `app/api/routers/` -- one FastAPI `APIRouter` per feature area:
  `catalog`, `dashboard`, `sell`, `backup`, `inward_stock`,
  `master_data`, `internal`.
- `app/core/` -- cross-cutting FastAPI concerns: `auth.py` (current-user
  dependencies), `xlsx_export.py` (streaming `.xlsx` responses),
  `errors.py` (domain `ValidationError` -> `400 JSON`).
- `app/integrations/users_client.py` -- placeholder HTTP client for the
  one cross-service call this makes into the Users service.
- `app/container.py` / `app/injector.py` -- the DI container
  (unchanged): `@singleton` registers a resource on import,
  `@injector` auto-fills constructor params from the container.
- `app/main.py` -- app factory; registers every router + the global
  error handler.

## What changed from the previous version

This service used to be two things bolted together: an already-FastAPI
catalog slice (`GET /books`, `GET /books/{id}`, `GET /health`) and a
separate legacy **Flask** app (Blueprint routes, `render_template`,
sessions, `flash()`, and Excel downloads via Flask's `send_file`) for
dashboard/sell/backup/inward-stock/master-data. That Flask half has
been ported to FastAPI and folded into this same package:

- Every route is now under `app/api/routers/`, one module per feature,
  each a small `APIRouter` -- no more one 300-line `routes.py`.
- Endpoints return JSON (or a streamed `.xlsx` for the export routes)
  instead of rendering HTML templates.
- Flask's `login_required`/`admin_required`/`current_user()` became
  FastAPI dependencies in `app/core/auth.py` (`get_current_user`,
  `require_admin`) -- currently backed by placeholder `X-User`/`X-Role`
  headers; swap `_resolve_user()` for real session/JWT verification.
- Flask's `request.form`/`request.args` became typed Pydantic request
  bodies (`app/models.py`) and `request.query_params`. The inward-stock
  batch endpoint in particular now takes a `rows: [...]` list in the
  JSON body instead of parallel `title[]`/`qty[]`/... form arrays (an
  HTML-form artifact that doesn't belong in a JSON API).
  `flash()` + redirect became a `{"message": ...}` field in the JSON
  response.
- `app_shared.xlxs.xlsx_export`'s `send_xlsx`/`send_xlsx_multi`
  (Flask `send_file`) became `app/core/xlsx_export.py`'s versions of
  the same two functions, returning a FastAPI `StreamingResponse`.
- `ValidationError` is now handled once, globally
  (`app/core/errors.py`), instead of per-route `try/except: flash(...)`.
- The old `backend.users.domain import get_user` in-process import (and
  the module-level `get_locations()`/`location_overview_data()`
  functions other services called directly) became a real HTTP
  boundary: `app/integrations/users_client.py` for the outbound call,
  and `app/api/routers/internal.py` for the inbound one -- this service
  runs as its own isolated pod (see `k8s-deployment.yaml`), so an
  in-process Python import across services was never actually going to
  work there.
- `app/models.py`'s duplicate `Book` class (declared once as a
  `BaseModel`, then again as a `dataclass` further down, silently
  shadowing the first) was consolidated into one `dataclass`, matching
  the `XCreate: BaseModel` / `X: dataclass` pattern already used for
  `SaleCreate`/`SaleRecord` and `PurchaseRowCreate`/`PurchaseRecord`.
- `app/domain.py` imported `from .db.db import books_db`, a module that
  was never actually included in this repo. `app/db/db.py` now
  provides that store as a small thread-safe in-memory implementation,
  so the service is importable and runnable without a real database
  wired up. Swap it for a persistence-backed implementation of the same
  methods (see that file's docstring) whenever you're ready -- nothing
  in `domain/` or `controllers/` needs to change.
- `app/services/book_service.py` (already marked "superseded by
  `app/domain/book_service.py`" in its own comment) was dropped; only
  the domain-layer version remains.

**Left untouched / out of scope:** the top-level `app.py` in this
archive builds a separate **Users** microservice (Flask, its own
Blueprint, its own templates) -- it isn't part of this Books package
and wasn't converted here.

## How to Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export SUPABASE_URL="https://your-supabase-url.supabase.co"
   export SUPABASE_KEY="your-supabase-anon-key"
   ```

3. Run the development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

4. Interactive API docs: `http://localhost:8000/docs`

## Auth (placeholder)

Every endpoint besides `/books`, `/books/{id}`, and `/health` expects
`X-User` (and optionally `X-Role: admin`) headers, e.g.:

```bash
curl -H "X-User: priya" -H "X-Role: admin" http://localhost:8000/api/dashboard
```

This is a stand-in for real session/JWT auth -- see
`app/core/auth.py`.
