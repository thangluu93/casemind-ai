"""Bounded read projections; persistence and actor authorization belong to the caller."""
from copy import deepcopy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .analytics import screening_analysis
from .models import Case, Evidence, digest

COLLECTION_LIMIT = 500
KNOWN_TOOLS = {
    "get_transactions", "trace_flows", "detect_cycles", "detect_structuring",
    "summarize_activity", "trace_ownership", "compare_ownership_declaration",
    "resolve_candidates", "get_relationships", "screen_candidates", "extract_document",
    "compare_fields",
}


class Scope(BaseModel):
    case_id: str
    run_id: str | None = None
    snapshot_id: str
    input_hash: str
    report_hash: str | None = None
    report_version: int | None = None


class FindingCard(BaseModel):
    id: str
    tool: str
    tool_version: int
    renderer: Literal["typed", "raw"]
    claim_kind: str
    verification_status: str
    refs: list[str]
    payload: dict[str, Any]
    parameters: dict[str, Any]
    limitations: list[str]


class WorkspaceView(BaseModel):
    version: int = 1
    scope: Scope
    classification: str = "synthetic"
    counts: dict[str, int]
    sources: list[dict[str, Any]]
    findings: list[FindingCard]
    screening_candidates: list[dict[str, Any]]
    coverage: dict[str, Any]
    hidden_counts: dict[str, int]


class ScreeningAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_ids: list[str] = Field(min_length=1, max_length=50)
    report_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_version: int = Field(ge=1)
    assessment: Literal["potential_match", "inconclusive", "likely_false_positive"]
    reason: str = Field(min_length=5, max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")

    @field_validator("reason")
    @classmethod
    def meaningful_reason(cls, value):
        value = value.strip()
        if len(value) < 5:
            raise ValueError("A meaningful assessment reason is required")
        return value


def bounded_limit(limit: int) -> int:
    if isinstance(limit, bool) or not 1 <= limit <= COLLECTION_LIMIT:
        raise ValueError(f"limit must be between 1 and {COLLECTION_LIMIT}")
    return limit


def snapshot_metadata(snapshot) -> dict:
    if isinstance(snapshot, BaseModel):
        return snapshot.model_dump(mode="json")
    return snapshot or {}


def scope_for(case: Case, report=None, snapshot=None) -> Scope:
    snapshot = snapshot_metadata(snapshot)
    if snapshot.get("case") is not None and Case.model_validate(snapshot["case"]) != case:
        raise ValueError("Snapshot case does not match selected case")
    input_hash = snapshot.get("snapshot_id") or digest(snapshot.get("raw_case") or case)
    if report and (report.get("case_id") != case.id or report.get("input_hash") != input_hash):
        raise ValueError("Report does not belong to the selected snapshot")
    if snapshot.get("input_hash", input_hash) != input_hash:
        raise ValueError("Snapshot hash does not match case")
    return Scope(case_id=case.id, run_id=report.get("run_id") if report else None,
                 snapshot_id=snapshot.get("snapshot_id", input_hash), input_hash=input_hash,
                 report_hash=report.get("hash") if report else None,
                 report_version=report.get("version") if report else None)


def evidence_for(case: Case, report, snapshot=None) -> list[Evidence]:
    scope_for(case, report, snapshot)
    items = [Evidence.model_validate(e) for e in (report or {}).get("evidence", [])]
    if len({e.id for e in items}) != len(items):
        raise ValueError("Duplicate evidence IDs")
    for e in items:
        if e.case_id != case.id or not set(e.refs) <= set(case.sources):
            raise ValueError("Evidence contains foreign sources")
        transactions = {tx.id for tx in case.transactions}
        if e.ordered_transaction_ids is not None and not set(e.ordered_transaction_ids) <= (set(e.refs) & transactions):
            raise ValueError("Ordered evidence contains foreign transactions")
        if e.participant_roles is not None and not set(e.participant_roles) <= (set(e.refs) & transactions):
            raise ValueError("Evidence roles contain foreign transactions")
        if e.target_transaction_id is not None and e.target_transaction_id not in (set(e.refs) & transactions):
            raise ValueError("Evidence target contains foreign transaction")
        for locator in e.document_lineage or []:
            if locator.get("document_id") not in {d.id for d in case.documents} & set(e.refs):
                raise ValueError("Evidence lineage contains foreign document")
    return items


def build_workspace(case: Case, report=None, snapshot=None, limit=200) -> WorkspaceView:
    limit = bounded_limit(limit)
    scope = scope_for(case, report, snapshot)
    evidence = evidence_for(case, report, snapshot)
    groups = {name: getattr(case, name) for name in (
        "entities", "accounts", "transactions", "relationships", "documents", "watchlist")}
    sources = [{"id": record.id, "type": name, "classification": record.source_kind,
                "origin": snapshot_metadata(snapshot).get("source_metadata", {}).get(record.id, {}).get("origin", "generated"),
                "source_object": (snapshot_metadata(snapshot).get("source_objects", {}).get(record.id)
                                  or snapshot_metadata(snapshot).get("source_metadata", {}).get(record.id, {}).get("source_object")),
                "locator": snapshot_metadata(snapshot).get("source_metadata", {}).get(record.id, {}).get("locator"),
                "record": record.model_dump(mode="json")}
               for name, records in groups.items() for record in records]
    screening = [e for e in (evidence if report else screening_analysis(case))
                 if e.tool == "screen_candidates" and "entity_id" in e.payload]
    candidates = [{"id": e.id, "evidence_id": e.id if report else None,
                   "refs": e.refs, **deepcopy(e.payload), "limitations": e.limitations}
                  for e in screening]
    cards = [FindingCard(id=e.id, tool=e.tool, tool_version=e.tool_version,
                        renderer="typed" if e.tool in KNOWN_TOOLS and e.tool_version in (1, 2) else "raw",
                        claim_kind=e.claim_kind, verification_status=e.verification_status,
                        refs=e.refs, payload=deepcopy(e.payload), parameters=e.parameters,
                        limitations=e.limitations) for e in evidence]
    return WorkspaceView(scope=scope, counts={k: len(v) for k, v in groups.items()},
                         sources=sources[:limit], findings=cards[:limit],
                         screening_candidates=candidates[:limit],
                         hidden_counts={"sources": max(0, len(sources)-limit),
                                        "findings": max(0, len(cards)-limit),
                                        "screening_candidates": max(0, len(candidates)-limit)},
                         coverage={"state": "run_evidence" if report else "not_evaluated",
                                   "gaps": deepcopy((report or {}).get("gaps", [])),
                                   "supplied_list_count": len(case.watchlist),
                                   "screening_state": "not_supplied" if not case.watchlist else
                                   "candidates_found" if candidates else "no_candidate",
                                   "limitations": ["Supplied-list screening is not clearance.",
                                                   "Indicators do not establish criminality."]})


def validate_screening_assessment(case: Case, report: dict,
                                  request: ScreeningAssessmentRequest | dict, snapshot=None) -> dict:
    request = ScreeningAssessmentRequest.model_validate(request)
    scope_for(case, report, snapshot)
    if request.report_hash != report["hash"] or request.expected_version != report["version"]:
        raise ValueError("Assessment report hash/version conflict")
    candidates = {e.id for e in evidence_for(case, report, snapshot)
                  if e.tool == "screen_candidates" and "entity_id" in e.payload}
    if not set(request.candidate_ids) <= candidates:
        raise ValueError("Candidate is not in the pinned report")
    result = request.model_dump(mode="json")
    result["candidate_ids"] = sorted(set(request.candidate_ids))
    result.update(run_id=report["run_id"], case_id=case.id, input_hash=report["input_hash"])
    result["request_hash"] = digest(result)
    return result
