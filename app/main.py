from dotenv import load_dotenv
import uvicorn

load_dotenv()

from fastapi import FastAPI
from app import container  # noqa: F401
from app.core.errors import register_error_handlers
from app.api.routers import backup, catalog, dashboard, internal, inward_stock, master_data, sell
from fastapi.middleware.cors import CORSMiddleware
import os


def create_app() -> FastAPI:
    app = FastAPI(
        title="Isolated Books API",
        description="FastAPI modular API using Contract Injection & Singleton resources",
        version="2.0.0",
    )

    register_error_handlers(app)

    app.include_router(catalog.router)
    app.include_router(dashboard.router)
    app.include_router(sell.router)
    app.include_router(backup.router)
    app.include_router(inward_stock.router)
    app.include_router(master_data.router)
    app.include_router(internal.router)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:5000")],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app  

app = create_app()


@app.get("/health", tags=["health"], summary="Health check")
def health_check():
    return {"status": "healthy", "pod": "isolated-books-api", "version": "2.0.0"}