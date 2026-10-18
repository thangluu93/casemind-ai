import hashlib

from .models import SourceObjectRef
from .store import Conflict


class SourceCatalog:
    def __init__(self, store):
        self.store = store

    def put(self, data: bytes, media_type: str) -> SourceObjectRef:
        sha = hashlib.sha256(data).hexdigest()
        key = "sha256/" + sha
        generation = self.store.put_blob_if_absent(key, data, media_type)
        return SourceObjectRef(sha256=sha, media_type=media_type, byte_size=len(data),
                               generation=generation, storage_key=key)

    def read(self, ref: SourceObjectRef | dict) -> bytes:
        ref = SourceObjectRef.model_validate(ref)
        data, generation = self.store.get_blob(ref.storage_key, ref.generation)
        if (generation != ref.generation or len(data) != ref.byte_size
                or hashlib.sha256(data).hexdigest() != ref.sha256):
            raise Conflict("Source object integrity mismatch")
        return data

    def stage(self, key: str, data: bytes, media_type: str, expected=0) -> int:
        if not key.startswith("staging/"):
            raise ValueError("Staging namespace required")
        return self.store.put_staging_blob(key, data, media_type, expected)

    def promote(self, key: str, generation: int, media_type: str) -> SourceObjectRef:
        if not key.startswith("staging/"):
            raise ValueError("Staging namespace required")
        data, _ = self.store.get_blob(key, generation)
        ref = self.put(data, media_type)
        self.store.delete_staging_blob(key, generation)
        return ref
