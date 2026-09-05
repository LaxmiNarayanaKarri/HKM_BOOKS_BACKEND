"""
`app/contracts/blob_store.py`

Generic JSON-blob storage contract -- same idea as `DBContract`, but
for Vercel Blob (or anything else that stores files at string paths)
instead of Postgres. Not Nidhi-specific on purpose: any future domain
that wants "one JSON file per record" storage can depend on this same
contract.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IBlobStore(ABC):
    """Abstract contract for path-addressed JSON blob storage."""

    @abstractmethod
    def put_json(self, path: str, data: Dict[str, Any]) -> str:
        """Write `data` as JSON to `path`, overwriting whatever is
        already there. Returns the blob's public URL."""
        raise NotImplementedError

    @abstractmethod
    def get_json(self, path: str) -> Optional[Dict[str, Any]]:
        """Read and parse the JSON blob at `path`. `None` if it
        doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def list_paths(self, prefix: str) -> List[str]:
        """Every blob pathname starting with `prefix`, e.g.
        `list_paths("transactions/alice/")`."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, path: str) -> None:
        """Remove the blob at `path`. No-op if it doesn't exist."""
        raise NotImplementedError