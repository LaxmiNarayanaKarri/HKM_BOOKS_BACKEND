import os

from app.injector import DBContract, FileStorageContract, injector, singleton


@singleton(FileStorageContract)
@injector
class SupabaseFileStorage(FileStorageContract):
    """Singleton file storage resource backed by a Supabase Storage bucket.

    Note this class itself declares a dependency (`db: DBContract`) and
    is decorated with @injector just like any consumer class -- the
    injector doesn't care whether the thing being built is a "resource"
    or a "service", so resources can depend on other resources the same
    way.
    """

    def __init__(self, db: DBContract, bucket: str = "book-covers"):
        self.db = db
        self.bucket = bucket or os.environ.get("SUPABASE_STORAGE_BUCKET", "book-covers")

    def _bucket_api(self):
        return self.db.get_client().storage.from_(self.bucket)

    def save(self, path: str, data: bytes) -> str:
        self._bucket_api().upload(path, data)
        return path

    def read(self, path: str) -> bytes:
        return self._bucket_api().download(path)

    def delete(self, path: str) -> None:
        self._bucket_api().remove([path])

    def exists(self, path: str) -> bool:
        try:
            listing = self._bucket_api().list(os.path.dirname(path) or None)
            names = {item.get("name") for item in (listing or [])}
            return os.path.basename(path) in names
        except Exception:
            return False
