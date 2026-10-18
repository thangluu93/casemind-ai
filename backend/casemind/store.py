import json
import os
import threading
import time
from pathlib import Path
from typing import Protocol

from google.api_core.exceptions import NotFound, PreconditionFailed, TooManyRequests


class Conflict(Exception):
    pass


class Store(Protocol):
    def get(self, key: str) -> tuple[dict | None, int]: ...
    def put(self, key: str, value: dict, expected: int = 0) -> int: ...
    def get_blob(self, key: str, generation: int | None = None) -> tuple[bytes, int]: ...
    def put_blob_if_absent(self, key: str, data: bytes, media_type: str) -> int: ...
    def put_staging_blob(self, key: str, data: bytes, media_type: str, expected: int = 0) -> int: ...
    def delete_staging_blob(self, key: str, generation: int) -> None: ...
    def scan_keys(self, prefix: str, cursor: str | None = None, limit: int = 100) -> tuple[list[str], str | None]: ...


class FileStore:
    """Single-process development adapter. Production always uses GCS CAS."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def path(self, key):
        validate_key(key)
        return self.root / (key + ".json")

    def get(self, key):
        with self.lock:
            path = self.path(key)
            if not path.exists():
                return None, 0
            envelope = json.loads(path.read_text())
            return envelope["data"], envelope["version"]

    def put(self, key, value, expected=0):
        with self.lock:
            _, version = self.get(key)
            if version != expected:
                raise Conflict("Artifact version changed")
            path = self.path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"version": version + 1, "data": value}))
            os.replace(temporary, path)
            return version + 1


class GCSStore:
    def __init__(self, client, bucket: str):
        self.bucket = client.bucket(bucket)

    def get(self, key):
        validate_key(key)
        blob = self.bucket.blob("artifacts/" + key + ".json")
        for _ in range(4):
            try:
                blob.reload(timeout=5, retry=None)
                return json.loads(
                    blob.download_as_text(
                        if_generation_match=blob.generation, timeout=5, retry=None
                    )
                ), int(blob.generation)
            except NotFound:
                return None, 0
            except PreconditionFailed:
                continue
        raise Conflict("Artifact changed repeatedly during read")

    def put(self, key, value, expected=0, backoff=(1, 2, 4)):
        validate_key(key)
        blob = self.bucket.blob("artifacts/" + key + ".json")
        # GCS allows about one mutation per second per object. A 429 rejects the write, and
        # the generation precondition keeps a later attempt from overwriting newer data.
        for delay in (*backoff, None):
            try:
                blob.upload_from_string(
                    json.dumps(value),
                    content_type="application/json",
                    if_generation_match=expected,
                    timeout=5,
                    retry=None,
                )
                return int(blob.generation)
            except PreconditionFailed as exc:
                raise Conflict("Artifact version changed") from exc
            except TooManyRequests:
                if delay is None:
                    raise
                time.sleep(delay)


def mutate(store: Store, key: str, transform):
    for _ in range(12):
        value, version = store.get(key)
        result = transform(value)
        try:
            store.put(key, result, version)
            return result
        except Conflict:
            continue
    raise Conflict("Too much concurrent activity; retry later")


class UsageLedger:
    # Reservations are conservative and retained on provider failure.
    def __init__(self, store: Store, max_runs=200, max_pages=200, session_runs=5):
        self.store, self.max_runs, self.max_pages, self.session_runs = (
            store,
            max_runs,
            max_pages,
            session_runs,
        )

    def reserve_run(self, session: str, run_id: str):
        def reserve(value):
            value = value or {"runs": {}, "pages": [], "sessions": {}}
            if run_id in value["runs"]:
                return value
            count = value["sessions"].get(session, 0)
            if len(value["runs"]) >= self.max_runs or count >= self.session_runs:
                raise ValueError(
                    "Investigation allowance exhausted; completed reports remain available"
                )
            value["runs"][run_id] = {"input_tokens_reserved": 50000, "output_tokens_reserved": 8000}
            value["sessions"][session] = count + 1
            return value

        mutate(self.store, "usage/prototype-v1", reserve)

    def reserve_page(self, document_hash: str):
        def reserve(value):
            value = value or {"runs": {}, "pages": [], "sessions": {}}
            # A retry still consumes a page, because the earlier call may have been billed.
            if len(value["pages"]) >= self.max_pages:
                raise ValueError("Document processing allowance exhausted")
            value["pages"].append(document_hash)
            return value

        mutate(self.store, "usage/prototype-v1", reserve)


    def reserve_pages(self, page_count: int, attempt_id: str, document_hash: str):
        if not 1 <= page_count <= 50 or not attempt_id:
            raise ValueError("Invalid document processing reservation")
        def reserve(value):
            value = value or {"runs": {}, "pages": [], "sessions": {}}
            prior = [p for p in value["pages"] if isinstance(p, dict) and p.get("attempt_id") == attempt_id]
            if prior:
                if len(prior) != page_count or any(p["document_hash"] != document_hash for p in prior):
                    raise Conflict("Document attempt reservation differs")
                return value
            if len(value["pages"]) + page_count > self.max_pages:
                raise ValueError("Document processing allowance exhausted")
            value["pages"].extend({"attempt_id": attempt_id, "document_hash": document_hash,
                                   "page": page + 1} for page in range(page_count))
            return value
        mutate(self.store, "usage/prototype-v1", reserve)


def validate_key(key):
    if not isinstance(key, str) or not key or key.startswith("/") or "\\" in key or any(
        p in ("", ".", "..") for p in key.split("/")
    ):
        raise ValueError("Invalid artifact key")


def _file_blob_path(self, key):
    validate_key(key)
    return self.root / "_blobs" / key


def _file_get_blob(self, key, generation=None):
    with self.lock:
        path = _file_blob_path(self, key)
        if not path.exists():
            raise KeyError(key)
        meta = json.loads(path.with_name(path.name + ".meta").read_text())
        if generation is not None and generation != meta["generation"]:
            raise Conflict("Object generation changed")
        return path.read_bytes(), meta["generation"]


def _file_stage(self, key, data, media_type, expected=0):
    with self.lock:
        path = _file_blob_path(self, key)
        try:
            _, current = self.get_blob(key)
        except KeyError:
            current = 0
        if current != expected:
            raise Conflict("Object generation changed")
        # Generation remains monotonic even after conditional deletion.
        counter = self.root / "_blob-generation"
        generation = int(counter.read_text()) + 1 if counter.exists() else 1
        counter.write_text(str(generation))
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        temp.write_bytes(data)
        os.replace(temp, path)
        path.with_name(path.name + ".meta").write_text(json.dumps(
            {"generation": generation, "media_type": media_type}))
        return generation


def _file_put_blob(self, key, data, media_type):
    with self.lock:
        try:
            existing, generation = self.get_blob(key)
        except KeyError:
            return _file_stage(self, key, data, media_type, expected=0)
        if existing != data:
            raise Conflict("Immutable object differs")
        return generation


def _file_delete(self, key, generation):
    with self.lock:
        self.get_blob(key, generation)
        path = _file_blob_path(self, key)
        path.unlink()
        path.with_name(path.name + ".meta").unlink()


def _file_scan(self, prefix, cursor=None, limit=100):
    validate_key(prefix.rstrip("/"))
    if not 1 <= limit <= 1000:
        raise ValueError("Scan limit must be 1..1000")
    keys = sorted(str(p.relative_to(self.root))[:-5] for p in self.root.rglob("*.json")
                  if "_blobs" not in p.relative_to(self.root).parts)
    keys = [k for k in keys if k.startswith(prefix) and (cursor is None or k > cursor)]
    page = keys[:limit]
    return page, page[-1] if len(keys) > limit else None


def _gcs_get_blob(self, key, generation=None):
    validate_key(key)
    blob = self.bucket.blob("objects/" + key, generation=generation)
    try:
        blob.reload(timeout=5, retry=None)
        actual = int(blob.generation)
        return blob.download_as_bytes(if_generation_match=actual, timeout=5, retry=None), actual
    except NotFound as exc:
        raise KeyError(key) from exc
    except PreconditionFailed as exc:
        raise Conflict("Object generation changed") from exc


def _gcs_stage(self, key, data, media_type, expected=0):
    validate_key(key)
    blob = self.bucket.blob("objects/" + key)
    try:
        blob.upload_from_string(data, content_type=media_type, if_generation_match=expected,
                                timeout=10, retry=None)
        return int(blob.generation)
    except PreconditionFailed as exc:
        raise Conflict("Object generation changed") from exc


def _gcs_put_blob(self, key, data, media_type):
    try:
        return _gcs_stage(self, key, data, media_type, expected=0)
    except Conflict:
        original, generation = self.get_blob(key)
        if original != data:
            raise Conflict("Immutable object differs")
        return generation


def _gcs_delete(self, key, generation):
    validate_key(key)
    try:
        self.bucket.blob("objects/" + key).delete(if_generation_match=generation,
                                                timeout=5, retry=None)
    except PreconditionFailed as exc:
        raise Conflict("Object generation changed") from exc


def _gcs_scan(self, prefix, cursor=None, limit=100):
    validate_key(prefix.rstrip("/"))
    if not 1 <= limit <= 1000:
        raise ValueError("Scan limit must be 1..1000")
    blobs = list(self.bucket.list_blobs(prefix="artifacts/" + prefix,
        start_offset=("artifacts/" + cursor + "\0") if cursor else None,
        max_results=limit + 1, timeout=10, retry=None))
    keys = [b.name[len("artifacts/"):-5] for b in blobs if b.name.endswith(".json")]
    page = keys[:limit]
    return page, page[-1] if len(keys) > limit else None


def _staging_writer(writer):
    def write(self, key, data, media_type, expected=0):
        if not key.startswith("staging/"):
            raise ValueError("Staging namespace required")
        return writer(self, key, data, media_type, expected)
    return write


def _staging_deleter(deleter):
    def delete(self, key, generation):
        if not key.startswith("staging/"):
            raise ValueError("Staging namespace required")
        return deleter(self, key, generation)
    return delete


# Shared adapter contract; JSON and immutable binary namespaces remain distinct.
FileStore.get_blob = _file_get_blob
FileStore.put_blob_if_absent = _file_put_blob
FileStore.put_staging_blob = _staging_writer(_file_stage)
FileStore.delete_staging_blob = _staging_deleter(_file_delete)
FileStore.scan_keys = _file_scan
GCSStore.get_blob = _gcs_get_blob
GCSStore.put_blob_if_absent = _gcs_put_blob
GCSStore.put_staging_blob = _staging_writer(_gcs_stage)
GCSStore.delete_staging_blob = _staging_deleter(_gcs_delete)
GCSStore.scan_keys = _gcs_scan
