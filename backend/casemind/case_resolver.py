"""Versioned immutable snapshot identity and explicit owner-scoped lookup."""
from .generator import document_pdf
from .models import ActorRef, Case, CaseManifest, SnapshotRef, digest
from .source_catalog import SourceCatalog


def snapshot_from_manifest(raw: dict) -> SnapshotRef:
    version = raw.get("manifest_version", 1)
    if version == 1:
        identity = digest(raw["case"])
    elif version == 2:
        manifest = CaseManifest.model_validate(raw)
        identity = digest(manifest.model_dump(mode="json", exclude={"hash", "table"}))
        if len(manifest.case.transactions) > 5000:
            raise ValueError("Snapshot exceeds 5000 total transactions")
    else:
        raise ValueError("Unsupported manifest version")
    if raw.get("hash") != identity:
        raise ValueError("Snapshot integrity mismatch")
    return SnapshotRef(case=Case.model_validate(raw["case"]), snapshot_id=identity,
                       manifest_version=version, raw_case=raw["case"], owner_id=raw.get("owner_id"), source_objects=raw.get("source_objects", {}),
                       source_metadata=raw.get("source_metadata", {}),
                       parent_snapshot_id=raw.get("parent_snapshot_id"))


def demo_snapshot(case: Case) -> SnapshotRef:
    return snapshot_from_manifest({"case": case.model_dump(mode="json"), "hash": digest(case)})


def snapshot_manifest(snapshot: SnapshotRef) -> dict:
    if snapshot.manifest_version == 1:
        raw = snapshot.raw_case if snapshot.raw_case is not None else snapshot.case.model_dump(mode="json")
        if digest(raw) != snapshot.snapshot_id:
            raise ValueError("Legacy snapshot identity mismatch")
        return {"case": raw, "hash": snapshot.snapshot_id}
    return CaseManifest(case=snapshot.case, source_objects=snapshot.source_objects,
                        source_metadata=snapshot.source_metadata,
                        parent_snapshot_id=snapshot.parent_snapshot_id,
                        hash=snapshot.snapshot_id, owner_id=snapshot.owner_id).model_dump(mode="json")


def create_manifest(case: Case, source_objects: dict, source_metadata: dict,
                    parent_snapshot_id: str | None = None, owner_id: str | None = None) -> dict:
    if len(case.transactions) > 5000:
        raise ValueError("Snapshot exceeds 5000 total transactions")
    metadata = {source_id: {"classification": "synthetic", "origin": "generated",
                            "locator": source_id} for source_id in case.sources}
    metadata.update(source_metadata)
    manifest = CaseManifest(case=case, source_objects=source_objects,
                            source_metadata=metadata, parent_snapshot_id=parent_snapshot_id, owner_id=owner_id)
    raw = manifest.model_dump(mode="json")
    raw["hash"] = digest(manifest.model_dump(mode="json", exclude={"hash", "table"}))
    return raw


class CaseResolver:
    def __init__(self, store, public_cases):
        self.store, self.public_cases = store, public_cases

    def owner(self, actor: ActorRef) -> str:
        alias, _ = self.store.get("owner-aliases/" + digest(actor.model_dump(mode="json")))
        return alias["owner_id"] if alias and alias.get("version") == 1 else actor.owner_id

    def resolve(self, case_id: str, actor: ActorRef | None = None) -> SnapshotRef:
        if case_id in self.public_cases:
            return demo_snapshot(self.public_cases[case_id])
        if actor is None:
            raise KeyError(case_id)
        owner_id = self.owner(actor)
        index, _ = self.store.get("owner-cases/" + digest(owner_id))
        snapshot_id = (index or {}).get("cases", {}).get(case_id)
        if not snapshot_id:
            raise KeyError(case_id)
        raw, _ = self.store.get(f"inputs/{case_id}/{snapshot_id}")
        if not raw or raw.get("owner_id") != owner_id:
            raise KeyError(case_id)
        return snapshot_from_manifest(raw)

    def document_bytes(self, snapshot: SnapshotRef, document_id: str) -> bytes:
        doc = next((d for d in snapshot.case.documents if d.id == document_id), None)
        if doc is None:
            raise KeyError(document_id)
        ref = snapshot.source_objects.get(document_id)
        if ref:
            return SourceCatalog(self.store).read(ref)
        if snapshot.manifest_version == 1:
            return document_pdf(doc)
        raise ValueError("Original document object unavailable")
