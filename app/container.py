"""
app/container.py

Bootstraps the DI container — import this once in main.py before
constructing any @injector-decorated class. Each import triggers the
@singleton registration in that module as a side-effect.
"""

from app.injector import container  # re-exported for convenience

# Infrastructure
import app.integrations.supabase_client   # noqa: F401  → DBContract
import app.storage.supabase_storage       # noqa: F401  → FileStorageContract

# Repositories  (one import per contract — order doesn't matter)
import app.repositories.supabase_book_repository        # noqa: F401  → IBookRepository
import app.repositories.supabase_location_repository    # noqa: F401  → ILocationRepository
import app.repositories.superbase_categories_repository # noqa: F401  → ICategoryRepository
import app.repositories.supabase_languages_repository   # noqa: F401  → ILanguageRepository
import app.repositories.supabase_events_repository      # noqa: F401  → IEventRepository
import app.repositories.supabase_purchase_repository    # noqa: F401  → IPurchaseRepository
import app.repositories.supabase_sources_repository     # noqa: F401  → ISourceRepository
import app.repositories.supabase_sales_repository       # noqa: F401  → ISalesRepository
import app.repositories.supabase_sell_entry_repository  # noqa: F401  → ISellEntryRepository
import app.repositories.supabase_stock_repository      # noqa: F401  → IStockRepository
import app.repositories.supabase_inventory_repository  # noqa: F401  → IInventoryRepository

__all__ = ["container"]