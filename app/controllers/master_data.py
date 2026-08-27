from typing import Optional

import app.domain.books_domain as bd
import app.domain.categories_domain as cd
import app.domain.languages_domain as ld
import app.domain.locations_domain as locd
import app.domain.events_domain as ed
import app.domain.sources_domain as sd


class MasterDataController:
    def __init__(
        self,
        books_domain: Optional[bd.BooksDomain] = None,
        categories_domain: Optional[cd.CategoriesDomain] = None,
        languages_domain: Optional[ld.LanguagesDomain] = None,
        locations_domain: Optional[locd.LocationsDomain] = None,
        events_domain: Optional[ed.EventsDomain] = None,
        sources_domain: Optional[sd.SourcesDomain] = None,
    ):
        self.books_domain = books_domain if books_domain is not None else bd.BooksDomain()
        self.categories_domain = categories_domain if categories_domain is not None else cd.CategoriesDomain()
        self.languages_domain = languages_domain if languages_domain is not None else ld.LanguagesDomain()
        self.locations_domain = locations_domain if locations_domain is not None else locd.LocationsDomain()
        self.events_domain = events_domain if events_domain is not None else ed.EventsDomain()
        self.sources_domain = sources_domain if sources_domain is not None else sd.SourcesDomain()

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

    # ------------------------------------------------------------------
    # Books
    # ------------------------------------------------------------------

    def add_book(self, title: str, short_title: Optional[str], threshold: Optional[int], category: Optional[int], language: Optional[int]) -> tuple:
        try:
            book = self.books_domain.create_book(
                title=title.strip(),
                short_title=short_title.strip() if short_title else None,
                threshold=threshold if threshold is not None else 0,
                category=category,
                language=language,
            )
            return book, True
        except ValueError:
            book = self.books_domain.get_book_by_title(title.strip())
            return book, False

    def update_book_threshold(self, title: str, threshold: int) -> None:
        """
        Updates the minimum stock threshold for an existing book.

        Args:
            title:     Exact book title used as the lookup key.
            threshold: New minimum stock value (must be >= 0).
        """
        self.books_domain.update_threshold(title=title, threshold=threshold)

    # ------------------------------------------------------------------
    # Book Categories
    # ------------------------------------------------------------------

    def add_category(self, name: str) -> None:
        """
        Adds a new book category to the reference list.

        Args:
            name: Category label (e.g. "Children's Books").
        """
        self.categories_domain.create_category(name=name.strip())

    # ------------------------------------------------------------------
    # Languages
    # ------------------------------------------------------------------

    def add_language(self, name: str) -> None:
        """
        Adds a new language to the reference list.

        Args:
            name: Language name (e.g. "Kannada").
        """
        self.languages_domain.create_language(name=name.strip())

    # ------------------------------------------------------------------
    # Locations
    # ------------------------------------------------------------------

    def add_location(self, name: str) -> None:
        """
        Adds a new distribution location to the reference list.

        Args:
            name: Location label (e.g. "Kukatpally Book Table").
        """
        self.locations_domain.create_location(name=name.strip())

    def list_locations(self) -> list:
        """
        Returns a list of all distribution locations.
        """
        return self.locations_domain.get_all_locations()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def add_event(self, name: str) -> None:
        """
        Adds a new event to the reference list.

        Args:
            name: Event name (e.g. "Janmashtami Festival").
        """
        self.events_domain.create_event(name=name.strip())

    def list_events(self) -> list:
        """
        Returns a list of all events.
        """
        return self.events_domain.list_events()


    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    def add_source(self, name: str) -> None:
        """
        Adds a new source to the reference list.

        Args:
            name: Source name (e.g. "Amazon").
        """
        self.sources_domain.create_source(name=name.strip())

    def list_sources(self) -> list:
        """
        Returns a list of all sources.
        """
        return self.sources_domain.list_sources()
    