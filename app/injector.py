"""
app/injector.py

Self-contained DI module for this service's shared *resources*
(database, file storage, ...). This replaces the `dependency_injector`
library usage in the old container.py with two plain decorators:

    @singleton(SomeContract)   -> register a concrete class as the one
                                   and only instance for that contract.
                                   Built lazily, on first use.

    @injector                  -> put on any class that *consumes*
                                   resources. Reads the constructor's
                                   type hints and auto-fills any
                                   parameter whose type is a registered
                                   contract, unless you passed it
                                   yourself.

Add a new contract here whenever you introduce a new kind of resource
(cache, queue, search index, ...). Wire the concrete implementation to
it with @singleton in that implementation's own module (e.g.
app/db/supabase_client.py), then consume it anywhere with @injector.
"""

from __future__ import annotations

import functools
import inspect
import threading
import typing
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Type, TypeVar

T = TypeVar("T")


# --------------------------------------------------------------------- #
# Contracts
# --------------------------------------------------------------------- #
class DBContract(ABC):
    """Contract for the database resource (Supabase, Postgres, ...)."""

    @abstractmethod
    def connect(self) -> None:
        """Open the underlying connection/client."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Close the underlying connection/client."""
        raise NotImplementedError

    @abstractmethod
    def get_client(self) -> Any:
        """Return the raw underlying client (e.g. the Supabase `Client`)."""
        raise NotImplementedError


class FileStorageContract(ABC):
    """Contract for the file storage resource (Supabase Storage, S3, local disk, ...)."""

    @abstractmethod
    def save(self, path: str, data: bytes) -> str:
        """Persist `data` at `path`. Returns the final stored path/URL."""
        raise NotImplementedError

    @abstractmethod
    def read(self, path: str) -> bytes:
        """Read and return the bytes stored at `path`."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete whatever is stored at `path`."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Return True if something is stored at `path`."""
        raise NotImplementedError


# --------------------------------------------------------------------- #
# Container
# --------------------------------------------------------------------- #
class ResourceNotRegistered(Exception):
    """Raised when resolving a contract that was never registered."""


class Container:
    def __init__(self) -> None:
        self._factories: Dict[type, Callable[[], object]] = {}
        self._singletons: Dict[type, object] = {}
        # RLock, not Lock: a singleton's own constructor is allowed to
        # resolve ANOTHER singleton (e.g. FileStorage depends on DB) --
        # that nested resolve() call happens on the same thread while
        # the outer resolve() still holds the lock. A plain Lock would
        # deadlock on that; RLock allows the same thread to re-acquire.
        self._lock = threading.RLock()

    def register(
        self,
        contract: Type[T],
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None,
    ) -> None:
        if instance is None and factory is None:
            raise ValueError("Must provide either `instance` or `factory`")
        with self._lock:
            if instance is not None:
                self._singletons[contract] = instance
                self._factories.pop(contract, None)
            else:
                self._factories[contract] = factory
                self._singletons.pop(contract, None)

    def has(self, contract: type) -> bool:
        return contract in self._factories or contract in self._singletons

    def resolve(self, contract: Type[T]) -> T:
        if contract in self._singletons:
            return self._singletons[contract]  # type: ignore[return-value]

        if contract not in self._factories:
            raise ResourceNotRegistered(
                f"No resource registered for contract '{contract.__name__}'. "
                f"Did you forget to import the module that @singleton-decorates it?"
            )

        # Double-checked locking: concurrent first-time resolutions only
        # ever build ONE instance.
        with self._lock:
            if contract not in self._singletons:
                factory = self._factories[contract]
                self._singletons[contract] = factory()
        return self._singletons[contract]  # type: ignore[return-value]

    def reset(self) -> None:
        """Clear all registrations. Mainly useful for test isolation."""
        with self._lock:
            self._factories.clear()
            self._singletons.clear()


# Single, shared, process-wide container. Import THIS everywhere.
container = Container()


# --------------------------------------------------------------------- #
# Decorators
# --------------------------------------------------------------------- #
def singleton(contract: type):
    """
    Class decorator: registers the decorated class as the singleton
    implementation of `contract`. Construction is deferred until the
    first time something actually resolves the contract (lazy).
    """

    def decorator(cls: Type[T]) -> Type[T]:
        container.register(contract, factory=lambda: cls())
        cls._di_contract = contract  # breadcrumb, useful when debugging
        return cls

    return decorator


def injector(cls: Type[T]) -> Type[T]:
    """
    Class decorator: auto-injects constructor parameters whose type hint
    matches a contract registered in the container. Explicit
    args/kwargs passed by the caller are always left untouched (handy
    for tests: `SupabaseBookRepository(db=FakeDB())` never gets
    overridden).
    """
    original_init = cls.__init__
    sig = inspect.signature(original_init)

    try:
        hints = typing.get_type_hints(original_init)
    except Exception:
        hints = getattr(original_init, "__annotations__", {})

    param_names = [name for name in sig.parameters if name != "self"]

    @functools.wraps(original_init)
    def new_init(self, *args, **kwargs):
        satisfied = set(param_names[: len(args)]) | set(kwargs.keys())
        for name in param_names:
            if name in satisfied:
                continue
            hint = hints.get(name)
            if hint is not None and container.has(hint):
                kwargs[name] = container.resolve(hint)
        original_init(self, *args, **kwargs)

    cls.__init__ = new_init
    return cls
