"""Bounded synthetic input staging and explicit whole-batch child construction."""
import csv
import hashlib
import io
import json
import re
import tempfile
import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .auth import owner_hash
from .case_resolver import create_manifest, snapshot_from_manifest
from .models import (Account, Case, Document, Entity, Relationship, Transaction,
                     WatchlistRecord, digest)
from .source_catalog import SourceCatalog
from .store import Conflict, mutate

GROUPS = {"entities": Entity, "accounts": Account, "transactions": Transaction,
          "relationships": Relationship, "documents": Document, "watchlist": WatchlistRecord}
CAPS = {"text/csv": 2 * 1024**2, "application/json": 1024**2,
        "application/pdf": 10 * 1024**2}


class IntakeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group: Literal["entities", "accounts", "transactions", "relationships", "documents", "watchlist"]
    action: Literal["add", "supersede"] = "add"
    record: dict[str, Any]
    target_revision: str | None = None
    source_object: dict[str, Any]
    locator: str
    classification: Literal["synthetic"] = "synthetic"
    origin: Literal["uploaded"] = "uploaded"


class IntakeBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    classification: Literal["synthetic"]
    records: list[IntakeRecord] = Field(max_length=6000)


async def stage_stream(stream, store, owner, follow_up_id, media_type, counters=None,
                       idempotency_key=None, expected_version=None, filename=None):
    """Count every decoded chunk before disk buffering; failure leaves no staged blob."""
    if media_type not in CAPS:
        raise ValueError("Only synthetic CSV, JSON and PDF inputs are accepted")
    counters = counters if counters is not None else {"bytes": 0, "pdfs": 0, "pages": 0}
    key = f"staging/{owner_hash(owner)}/{digest(follow_up_id)}/{time.time_ns()}"
    size, hasher, generation = 0, hashlib.sha256(), None
    try:
        with tempfile.TemporaryFile() as temporary:
            async for chunk in stream:
                size += len(chunk)
                counters["bytes"] = counters.get("bytes", 0) + len(chunk)
                if size > CAPS[media_type] or counters["bytes"] > 32 * 1024**2:
                    raise ValueError("Decoded intake size limit exceeded")
                hasher.update(chunk)
                temporary.write(chunk)
            if not size:
                raise ValueError("Empty input")
            temporary.seek(0)
            data = temporary.read(CAPS[media_type] + 1)
        request_key = None
        if idempotency_key:
            request_key = (f"staging-requests/{owner_hash(owner)}/{digest(follow_up_id)}/"
                           + digest(idempotency_key))
            canonical = digest({"media_type": media_type, "sha256": hasher.hexdigest(),
                                "expected_version": expected_version, "filename": filename})
            prior, _ = store.get(request_key)
            if prior:
                if prior["hash"] != canonical:
                    raise Conflict("Upload key reused with different bytes or parameters")
                if prior.get("result"):
                    return prior["result"]
            else:
                try:
                    store.put(request_key, {"hash": canonical, "created": time.time()})
                except Conflict:
                    prior, _ = store.get(request_key)
                    if prior["hash"] != canonical:
                        raise Conflict("Upload key reused with different bytes or parameters")
            key = f"staging/{owner_hash(owner)}/{digest(follow_up_id)}/{digest(idempotency_key)}"
        if media_type == "application/pdf":
            from .document_rendering import render_document
            pages = len(render_document(data, {"sha256": hasher.hexdigest(),
                "media_type": media_type, "byte_size": size, "generation": 1,
                "storage_key": key}))
            counters["pdfs"] = counters.get("pdfs", 0) + 1
            counters["pages"] = counters.get("pages", 0) + pages
            if counters["pdfs"] > 10 or counters["pages"] > 50:
                raise ValueError("PDF request page or document limit exceeded")
        else:
            pages = 0
        try:
            generation = store.put_staging_blob(key, data, media_type)
        except Conflict:
            if not request_key:
                raise
            existing_data, generation = store.get_blob(key)
            if existing_data != data:
                raise Conflict("Upload staging bytes changed")
        descriptor = {"key": key, "generation": generation, "media_type": media_type,
                "sha256": hasher.hexdigest(), "byte_size": size, "verified_page_count": pages,
                "created": (store.get(request_key)[0]["created"] if request_key else time.time()),
                "classification": "synthetic", "origin": "uploaded"}
        budget_key = f"staged/{owner_hash(owner)}/{digest(follow_up_id)}"
        def reserve(old):
            old = old or {"objects": {}}
            if key in old["objects"]:
                return old
            if sum(item["byte_size"] for item in old["objects"].values()) + size > 64 * 1024**2:
                raise ValueError("Follow-up staged size limit exceeded")
            return {"objects": old["objects"] | {key: descriptor}}
        mutate(store, budget_key, reserve)
        if request_key:
            mutate(store, request_key, lambda prior: prior | {"result": descriptor})
        return descriptor
    except BaseException:
        if generation is not None:
            store.delete_staging_blob(key, generation)
        raise


def parse_batch(data: bytes, media_type: str, source_object: dict) -> IntakeBatch:
    if len(data) > CAPS.get(media_type, 0):
        raise ValueError("Input size limit exceeded")
    if media_type == "application/json":
        raw = json.loads(data.decode("utf-8"))
        if not isinstance(raw, dict) or raw.get("classification") != "synthetic":
            raise ValueError("Explicit synthetic classification is required")
        records = raw.get("records", [])
        if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
            raise ValueError("JSON records must be an array of typed objects")
        if len(records) > 1000:
            raise ValueError("JSON record limit exceeded")
        records = [item | {"source_object": source_object,
                           "locator": f"records/{index}"} for index, item in enumerate(records)]
        return IntakeBatch.model_validate(raw | {"records": records})
    if media_type == "text/csv":
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
        records = []
        for index, row in enumerate(reader):
            if index >= 5000:
                raise ValueError("CSV row limit exceeded")
            if row.pop("classification", None) != "synthetic":
                raise ValueError("Every CSV row requires synthetic classification")
            group, action = row.pop("group", "transactions"), row.pop("action", "add")
            revision = row.pop("target_revision", None) or None
            record = {key: value for key, value in row.items() if value != ""}
            for name in ("identifiers", "fields"):
                if name in record:
                    record[name] = json.loads(record[name])
            records.append(IntakeRecord(group=group, action=action, target_revision=revision,
                                        record=record, source_object=source_object,
                                        locator=f"row/{index + 2}"))
        return IntakeBatch(classification="synthetic", records=records)
    raise ValueError("PDFs require explicit typed document metadata")


def validate_batch(parent: Case, batch: IntakeBatch):
    """Validate all forward references; quarantine dependency closures without silent drops."""
    accepted, quarantine, claimed = [], [], set()
    counts = {}
    for item in batch.records:
        identity = digest(item.record.get("id"))
        counts[identity] = counts.get(identity, 0) + 1
    for item in sorted(batch.records, key=lambda item: (item.group, str(item.record.get("id", "")),
                                                      digest(item.model_dump(mode="json")))):
        reason = None
        try:
            record = GROUPS[item.group].model_validate(item.record)
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:_-]{0,127}", record.id):
                raise ValueError("Stable source IDs must be bounded URL-safe identifiers")
            if any("http://" in str(v) or "https://" in str(v) for v in item.record.values()):
                raise ValueError("Remote URLs are not accepted intake sources")
            if counts.get(digest(record.id), 0) > 1 or record.id in claimed:
                raise ValueError("Conflicting batch stable ID")
            claimed.add(record.id)
            previous = parent.sources.get(record.id)
            if item.action == "add" and previous:
                raise ValueError("Add collides with existing stable ID")
            if item.action == "supersede" and (not previous or not isinstance(previous, GROUPS[item.group])
                    or item.target_revision != digest(previous)):
                raise ValueError("Supersede requires exact existing stable ID and revision")
            accepted.append((item, record))
        except (ValueError, TypeError) as exc:
            reason = str(exc)
        if reason:
            quarantine.append({"input": item.model_dump(mode="json"), "reason": reason})
    while True:
        groups = {name: {record.id: record for record in getattr(parent, name)} for name in GROUPS}
        for item, record in accepted:
            groups[item.group][record.id] = record
        entity_ids, account_ids = set(groups["entities"]), set(groups["accounts"])
        rejected = []
        for item, record in accepted:
            dangling = ((item.group == "accounts" and record.entity_id not in entity_ids)
                        or (item.group == "transactions" and
                            (record.sender not in account_ids or record.receiver not in account_ids))
                        or (item.group == "relationships" and
                            (record.owner not in entity_ids or record.owned not in entity_ids))
                        or (item.group == "documents" and record.entity_id not in entity_ids))
            if dangling:
                rejected.append((item, record))
                quarantine.append({"input": item.model_dump(mode="json"),
                                   "reason": "Unresolved dependency in parent plus accepted batch"})
        if not rejected:
            break
        accepted = [pair for pair in accepted if pair not in rejected]
    if len(groups["transactions"]) > 5000:
        raise ValueError("Parent plus intake exceeds five thousand transactions")
    raw = parent.model_dump(mode="json")
    for name, records in groups.items():
        raw[name] = [records[key].model_dump(mode="json") for key in sorted(records)]
    child = Case.model_validate(raw)
    return child, [item for item, _ in accepted], quarantine


def commit_child(store, owner, parent_snapshot, batch: IntakeBatch):
    child, accepted, quarantine = validate_batch(parent_snapshot.case, batch)
    sources = dict(parent_snapshot.source_objects)
    metadata = dict(parent_snapshot.source_metadata)
    catalog = SourceCatalog(store)
    # V2 requires exact originals for inherited demo documents as well.
    from .generator import document_pdf
    for document in parent_snapshot.case.documents:
        if document.id not in sources:
            sources[document.id] = catalog.put(document_pdf(document), "application/pdf")
    for item in accepted:
        catalog.read(item.source_object)
        metadata[item.record["id"]] = {"origin": "uploaded", "classification": "synthetic",
                                      "locator": item.locator, "source_object": item.source_object}
        if item.group == "documents":
            if item.source_object.get("media_type") != "application/pdf":
                raise ValueError("Imported documents require original PDF objects")
            sources[item.record["id"]] = item.source_object
    identity = digest([parent_snapshot.snapshot_id,
                       sorted((item.model_dump(mode="json") for item in accepted), key=digest)])
    child = child.model_copy(update={"id": "imported-" + identity[:24], "schema_version": 2})
    raw = create_manifest(child, sources, metadata, parent_snapshot.snapshot_id)
    raw["owner_id"] = owner
    from .models import CaseManifest
    raw["hash"] = digest(CaseManifest.model_validate(raw).model_dump(mode="json", exclude={"hash", "table"}))
    key = f"inputs/{child.id}/{raw['hash']}"
    try:
        store.put(key, raw)
    except Conflict:
        existing, _ = store.get(key)
        if existing != raw:
            raise Conflict("Immutable child manifest conflict")
    def index(old):
        old = old or {"cases": {}}
        return old | {"cases": old["cases"] | {child.id: raw["hash"]}}
    mutate(store, "owner-cases/" + digest(owner), index)
    canonical_batch = batch.model_dump(mode="json")
    canonical_batch["records"] = sorted(canonical_batch["records"], key=digest)
    audit_key = f"intake/{owner_hash(owner)}/{raw['hash']}/{digest(canonical_batch)}"
    audit = {"batch": canonical_batch, "quarantine": sorted(quarantine, key=digest),
             "child_snapshot": raw["hash"], "parent_snapshot": parent_snapshot.snapshot_id}
    try:
        store.put(audit_key, audit)
    except Conflict:
        if store.get(audit_key)[0] != audit:
            raise Conflict("Intake audit conflict")
    return snapshot_from_manifest(raw), quarantine


def promote_staged(store, owner, follow_up_id, descriptor):
    prefix = f"staging/{owner_hash(owner)}/{digest(follow_up_id)}/"
    if not descriptor["key"].startswith(prefix):
        raise PermissionError("Staged object is outside this follow-up")
    ref = SourceCatalog(store).promote(descriptor["key"], descriptor["generation"],
                                       descriptor["media_type"])
    def remove(old):
        objects = dict((old or {}).get("objects", {}))
        objects.pop(descriptor["key"], None)
        return {"objects": objects}
    mutate(store, f"staged/{owner_hash(owner)}/{digest(follow_up_id)}", remove)
    return ref


def sweep_staging(store, owner, cursor=None, limit=100, now=None):
    now = time.time() if now is None else now
    keys, cursor = store.scan_keys(f"staged/{owner_hash(owner)}/", cursor=cursor, limit=limit)
    removed = 0
    for key in keys:
        value, _ = store.get(key)
        for descriptor in list((value or {}).get("objects", {}).values()):
            if descriptor["created"] + 3600 > now:
                continue
            store.delete_staging_blob(descriptor["key"], descriptor["generation"])
            def remove(old):
                objects = dict((old or {}).get("objects", {}))
                objects.pop(descriptor["key"], None)
                return {"objects": objects}
            mutate(store, key, remove)
            removed += 1
    return {"removed": removed, "cursor": cursor}


def discard_staged(store, owner, follow_up_id, descriptor):
    """Discard both object and CAS accounting after a rejected route command."""
    prefix = f"staging/{owner_hash(owner)}/{digest(follow_up_id)}/"
    if not descriptor["key"].startswith(prefix):
        raise PermissionError("Staged object is outside this follow-up")
    store.delete_staging_blob(descriptor["key"], descriptor["generation"])
    def remove(old):
        objects = dict((old or {}).get("objects", {}))
        objects.pop(descriptor["key"], None)
        return {"objects": objects}
    mutate(store, f"staged/{owner_hash(owner)}/{digest(follow_up_id)}", remove)
