from typing import Optional

import app.domain.books_domain as bd


class MasterDataController:
    def __init__(
        self,
        books_domain: Optional[bd.BooksDomain] = None,
    ):
        self.books_domain = books_domain if books_domain is not None else bd.BooksDomain()

    # ------------------------------------------------------------------
    # Page load — fetch all reference lists in one call
    # ------------------------------------------------------------------

    def get_master_data(self) -> dict:
        """
        Returns every reference list the master data page needs.
        Maps directly to the Jinja context variables:
            books, categories, languages, locations, events
        """
        return {
            "books": self.books_domain.list_books(),
            "categories": self.categories_domain.list_categories(),
            "languages": self.languages_domain.list_languages(),
            "locations": self.locations_domain.list_locations(),
            "events": self.events_domain.list_events(),
        }