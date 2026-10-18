import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def digest(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    source_kind: Literal["synthetic"] = "synthetic"


class Entity(Record):
    name: str
    kind: Literal["person", "company"]
    country: str = "XX"
    identifiers: dict[str, str] = Field(default_factory=dict)


class Account(Record):
    entity_id: str
    bank_id: str = "bank:synthetic"


class Transaction(Record):
    sender: str
    receiver: str
    amount: Decimal = Field(gt=0)
    currency: str = "USD"
    timestamp: datetime

    @field_validator("amount", mode="before")
    @classmethod
    def no_float_money(cls, value):
        if isinstance(value, float):
            raise ValueError("Money must be a decimal string or Decimal")
        return value

    @field_validator("timestamp")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError("Timezone is required")
        return value


class Relationship(Record):
    owner: str
    owned: str
    percentage: Decimal | None = Field(default=None, ge=0, le=100)
    relationship_type: Literal["shareholding"] = "shareholding"


class Document(Record):
    entity_id: str
    kind: str
    fields: dict[str, str]


class WatchlistRecord(Record):
    name: str
    category: Literal["sanctions", "pep"]
    identifiers: dict[str, str] = Field(default_factory=dict)


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    description: str = "Fictional records for investigator review; no real persons or businesses."
    schema_version: int = 1
    generator_version: int = 1
    seed: int
    entities: list[Entity]
    accounts: list[Account]
    transactions: list[Transaction]
    relationships: list[Relationship]
    documents: list[Document]
    watchlist: list[WatchlistRecord]

    @property
    def sources(self) -> dict[str, Record]:
        return {
            r.id: r
            for group in (
                self.entities,
                self.accounts,
                self.transactions,
                self.relationships,
                self.documents,
                self.watchlist,
            )
            for r in group
        }

    @model_validator(mode="after")
    def validate_links(self):
        groups = (
            self.entities,
            self.accounts,
            self.transactions,
            self.relationships,
            self.documents,
            self.watchlist,
        )
        ids = [r.id for group in groups for r in group]
        if len(ids) != len(set(ids)):
            raise ValueError("Source IDs must be unique")
        entity_ids = {r.id for r in self.entities}
        account_ids = {r.id for r in self.accounts}
        if any(a.entity_id not in entity_ids for a in self.accounts):
            raise ValueError("Unknown account entity")
        if any(
            t.sender not in account_ids or t.receiver not in account_ids for t in self.transactions
        ):
            raise ValueError("Unknown transaction account")
        if any(r.owner not in entity_ids or r.owned not in entity_ids for r in self.relationships):
            raise ValueError("Unknown relationship entity")
        if any(d.entity_id not in entity_ids for d in self.documents):
            raise ValueError("Unknown document entity")
        return self


class Evidence(BaseModel):
    id: str
    case_id: str
    tool: str
    tool_version: int = 1
    source_kind: Literal["synthetic"] = "synthetic"
    claim_kind: Literal["observation", "indicator"]
    verification_status: Literal["source_supported"] = "source_supported"
    refs: list[str]
    payload: dict[str, Any]
    parameters: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    ordered_transaction_ids: list[str] | None = None
    participant_roles: dict[str, str] | None = None
    target_transaction_id: str | None = None
    coverage: dict[str, Any] | None = None
    document_lineage: list[dict[str, Any]] | None = None


class ReportClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(max_length=1600)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)


class Synthesis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(max_length=2000)
    hypotheses: list[ReportClaim] = Field(max_length=12)
    alternatives: list[str] = Field(max_length=12)
    unresolved: list[str] = Field(max_length=12)


class StartRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_version: int = Field(ge=1)
    action: Literal["approved", "rejected", "needs_follow_up"]
    reason: str = Field(min_length=5, max_length=2000)

    @field_validator("reason")
    @classmethod
    def meaningful_reason(cls, value):
        value = value.strip()
        if len(value) < 5:
            raise ValueError("A meaningful review reason is required")
        return value


class ActorRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["session", "google"]
    owner_id: str = Field(min_length=1, max_length=256)


class SourceObjectRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    media_type: str = Field(min_length=1, max_length=100)
    byte_size: int = Field(ge=0)
    generation: int = Field(gt=0)
    storage_key: str

    @field_validator("storage_key")
    @classmethod
    def safe_storage_key(cls, value):
        from .store import validate_key
        validate_key(value)
        return value


class SourceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    locator: str | None = None
    source_object: SourceObjectRef | None = None
    classification: Literal["synthetic"] = "synthetic"
    origin: Literal["generated", "uploaded"]


class SnapshotRef(BaseModel):
    case: Case
    snapshot_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    manifest_version: Literal[1, 2] = 1
    raw_case: dict[str, Any] | None = None
    owner_id: str | None = None
    source_objects: dict[str, SourceObjectRef] = Field(default_factory=dict)
    source_metadata: dict[str, SourceMetadata] = Field(default_factory=dict)
    parent_snapshot_id: str | None = None


class CaseManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    manifest_version: Literal[2] = 2
    case: Case
    source_objects: dict[str, SourceObjectRef]
    source_metadata: dict[str, SourceMetadata]
    parent_snapshot_id: str | None = None
    hash: str = ""
    table: str | None = None
    owner_id: str | None = None
