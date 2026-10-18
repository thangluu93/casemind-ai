"""Deterministic investigator insights derived from a pinned snapshot and recorded evidence.

Nothing here writes to a report. Each view states its rule set and what was not evaluated.
"""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .analytics import (DEFAULT_RULES, detect_structuring, normalize, rules,
                        summarize_activity, trace_flows)
from .models import Case, Evidence, digest
from .priority import follow_up_priority

TOOL_FAMILIES = {
    "transaction": {"get_transactions", "trace_flows", "detect_cycles", "detect_structuring",
                    "summarize_activity"},
    "entity": {"trace_ownership", "compare_ownership_declaration", "resolve_candidates",
               "get_relationships"},
    "compliance": {"screen_candidates"},
    "document": {"extract_document", "compare_fields", "detect_embedded_instructions"},
}
TRIAGE_WEIGHTS = {"trace_flows": 10, "detect_cycles": 25, "detect_structuring": 20,
                  "compare_ownership_declaration": 20, "screen_candidates": 25,
                  "compare_fields": 20, "detect_embedded_instructions": 20,
                  "summarize_activity": 5, "trace_ownership": 15}

# Demonstration mapping inspired by public money-laundering typology categories.
TYPOLOGIES = [
    {"id": "rapid_pass_through", "name": "Layering through rapid pass-through",
     "family": "transaction",
     "indicators": [("trace_flows", None, "Funds move onward within the window while most value is retained")]},
    {"id": "round_tripping", "name": "Round-tripping", "family": "transaction",
     "indicators": [("detect_cycles", None, "Value returns to the originating account through intermediaries")]},
    {"id": "structuring", "name": "Structuring below a threshold", "family": "transaction",
     "indicators": [("detect_structuring", None, "Several sub-threshold transfers within a short window")]},
    {"id": "activity_spike", "name": "Unusual activity against the account baseline",
     "family": "transaction",
     "indicators": [("summarize_activity", None, "A transfer far above the sender's median")]},
    {"id": "opaque_ownership", "name": "Opaque or inconsistent ownership", "family": "entity",
     "indicators": [
         ("compare_ownership_declaration", None, "Declared owner differs from the traced candidate"),
         ("trace_ownership", "unresolved_cycle_or_depth", "Ownership chain is cyclic or too deep"),
         ("trace_ownership", "candidate_requires_review", "Natural-person candidate above the review threshold"),
     ]},
    {"id": "sanctions_pep_exposure", "name": "Sanctions or PEP exposure", "family": "compliance",
     "indicators": [
         ("screen_candidates", "potential_match", "Name and identifiers agree with a list record"),
         ("screen_candidates", "inconclusive", "Name agrees but identifiers are incomplete"),
     ]},
    {"id": "document_inconsistency", "name": "Inconsistent customer documentation",
     "family": "document",
     "indicators": [
         ("compare_fields", "declared_field_mismatch", "Document field differs from the declared value"),
         ("compare_fields", "cross_document_mismatch", "Documents disagree with each other"),
     ]},
    {"id": "document_tampering_attempt", "name": "Document content attempting to direct review",
     "family": "document",
     "indicators": [("detect_embedded_instructions", None, "Document text contains reviewer or model instructions")]},
]
TYPOLOGY_NOTE = ("Demonstration mapping to public typology categories. A matched indicator is a "
                 "reason for review, not a determination of money laundering or criminality.")


def _evidence(report: dict | None) -> list[Evidence]:
    return [Evidence.model_validate(e) for e in (report or {}).get("evidence", [])]


def evaluated_families(evidence: list[Evidence], report: dict | None) -> set[str]:
    failed = {gap.get("role") for gap in (report or {}).get("gaps", [])}
    tools = {e.tool for e in evidence}
    return {family for family, members in TOOL_FAMILIES.items()
            if tools & members and family not in failed}


# Statuses that are recorded as observations but still describe an unresolved risk.
OBSERVATION_STATUSES = {"unresolved_cycle_or_depth", "inconclusive"}


def _matches(item: Evidence, tool: str, status: str | None) -> bool:
    if item.tool != tool:
        return False
    if status is None:
        return item.claim_kind == "indicator"
    return item.payload.get("status") == status and (
        item.claim_kind == "indicator" or status in OBSERVATION_STATUSES)


def typology_map(case: Case, report: dict) -> dict:
    evidence = _evidence(report)
    families = evaluated_families(evidence, report)
    result = []
    for typology in TYPOLOGIES:
        indicators = []
        for tool, status, description in typology["indicators"]:
            ids = sorted(e.id for e in evidence if _matches(e, tool, status))
            state = ("observed" if ids else "evaluated_not_observed"
                     if typology["family"] in families else "not_evaluated")
            indicators.append({"tool": tool, "status_filter": status, "description": description,
                               "state": state, "evidence_ids": ids})
        observed = sum(i["state"] == "observed" for i in indicators)
        result.append({"id": typology["id"], "name": typology["name"],
                       "family": typology["family"], "indicators": indicators,
                       "observed_indicator_count": observed,
                       "state": "observed" if observed else indicators[0]["state"]})
    result.sort(key=lambda t: (-t["observed_indicator_count"], t["id"]))
    return {"case_id": case.id, "typologies": result, "evaluated_families": sorted(families),
            "mapping_version": 1, "limitations": [TYPOLOGY_NOTE]}


class ThresholdSimulation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flow_minimum_amount: Decimal | None = Field(default=None, gt=0, le=Decimal("100000000"))
    flow_window_hours: int | None = Field(default=None, ge=1, le=720)
    flow_minimum_retained_ratio: Decimal | None = Field(default=None, gt=0, le=1)
    flow_maximum_retained_ratio: Decimal | None = Field(default=None, ge=1, le=2)
    structuring_threshold: Decimal | None = Field(default=None, gt=0, le=Decimal("100000000"))
    structuring_window_hours: int | None = Field(default=None, ge=1, le=720)
    structuring_minimum_count: int | None = Field(default=None, ge=2, le=50)
    activity_median_multiple: int | None = Field(default=None, ge=2, le=100)

    @field_validator("flow_minimum_amount", "flow_minimum_retained_ratio",
                     "flow_maximum_retained_ratio", "structuring_threshold", mode="before")
    @classmethod
    def no_float(cls, value):
        if isinstance(value, float):
            raise ValueError("Use decimal strings for amounts and ratios")
        return value


SIMULATED_TOOLS = (("trace_flows", trace_flows), ("detect_cycles", trace_flows),
                   ("detect_structuring", detect_structuring),
                   ("summarize_activity", summarize_activity))


def _flagged(evidence: list[Evidence], tool: str) -> set[str]:
    flagged = set()
    for item in evidence:
        if item.tool == tool and item.claim_kind == "indicator":
            target = item.target_transaction_id
            flagged.update([target] if target else item.ordered_transaction_ids or [])
    return flagged


def simulate_thresholds(case: Case, report: dict, overrides: ThresholdSimulation) -> dict:
    params = {k: v for k, v in overrides.model_dump().items() if v is not None}
    effective = rules(params)
    if effective["flow_minimum_retained_ratio"] > effective["flow_maximum_retained_ratio"]:
        raise ValueError("Minimum retained ratio exceeds the maximum")
    recorded = _evidence(report)
    computed = {}
    tools = []
    for tool, function in SIMULATED_TOOLS:
        if function not in computed:
            computed[function] = function(case, params)
        before, after = _flagged(recorded, tool), _flagged(computed[function], tool)
        tools.append({"tool": tool, "recorded_flagged": sorted(before),
                      "simulated_flagged": sorted(after), "added": sorted(after - before),
                      "removed": sorted(before - after),
                      "recorded_indicator_count": sum(
                          e.tool == tool and e.claim_kind == "indicator" for e in recorded),
                      "simulated_indicator_count": sum(
                          e.tool == tool and e.claim_kind == "indicator"
                          for e in computed[function])})
    return {"case_id": case.id, "persisted": False,
            "parameters": {k: str(v) for k, v in effective.items()},
            "defaults": {k: str(v) for k, v in DEFAULT_RULES.items()},
            "changed_parameters": sorted(params), "tools": tools,
            "changed": any(t["added"] or t["removed"] for t in tools),
            "limitations": ["Simulation only; the pinned report and its review are unchanged.",
                            "Rules are demonstration parameters, not legal reporting thresholds."]}


def _driver(question, request_type, affects, impact_tool, rationale, effect, refs=()):
    affects = sorted(set(affects))
    return {"id": "cd-" + digest([question, affects])[:16], "question": question,
            "_tool": impact_tool,
            "request_type": request_type, "affects_evidence_ids": affects,
            "source_refs": sorted(set(refs)), "effect": effect,
            "impact_score": TRIAGE_WEIGHTS.get(impact_tool, 5) * max(1, len(affects)),
            "rationale": rationale}


def change_drivers(case: Case, report: dict) -> dict:
    """Missing information ranked by the triage weight of the findings it would resolve."""
    evidence = _evidence(report)
    drivers = []
    for rel in case.relationships:
        if rel.percentage is None:
            affected = [e.id for e in evidence if rel.id in e.refs]
            drivers.append(_driver(
                "What is the recorded shareholding percentage for this relationship?",
                "ownership_register", affected, "trace_ownership",
                "Unknown percentages stop the per-path calculation.", "resolves_unknown", [rel.id]))
    entities = {e.id: e for e in case.entities}
    watch = {w.id: w for w in case.watchlist}
    for item in evidence:
        status = item.payload.get("status")
        if item.tool == "screen_candidates" and status in ("potential_match", "inconclusive"):
            entity = entities.get(item.payload.get("entity_id"))
            record = watch.get(item.payload.get("watchlist_id"))
            if entity and record:
                missing = sorted((set(entity.identifiers) ^ set(record.identifiers))
                                 - {"beneficial_owner"})
                drivers.append(_driver(
                    "Which additional identifiers confirm or exclude this list candidate"
                    + (f" (missing on one side: {', '.join(missing)})?" if missing else "?"),
                    "identity_verification", [item.id], "screen_candidates",
                    "Identifier agreement decides between a match and a false positive.",
                    "could_confirm_or_exclude", item.refs))
        elif item.tool == "compare_fields" and status in ("unresolved_low_confidence",
                                                          "unresolved_missing_fields"):
            drivers.append(_driver("Can a legible original of this document be obtained?",
                                   "document_copy", [item.id], "compare_fields",
                                   "Unreadable fields leave the document comparison unresolved.",
                                   "resolves_unknown", item.refs))
        elif item.tool == "compare_ownership_declaration":
            drivers.append(_driver(
                "Is there a dated ownership change that explains the declaration difference?",
                "ownership_history", [item.id], "compare_ownership_declaration",
                "Dates are not supplied, so timing cannot be evaluated.",
                "could_support_alternative", item.refs))
        elif item.tool in ("trace_flows", "detect_cycles") and item.claim_kind == "indicator":
            drivers.append(_driver(
                "What contracts or invoices support these onward transfers?",
                "transaction_purpose", [item.id], item.tool,
                "Documented commercial purpose is the main legitimate alternative.",
                "could_support_alternative", item.ordered_transaction_ids or item.refs))
        elif item.tool == "detect_structuring":
            drivers.append(_driver("What is the customer's stated purpose for this series of payments?",
                                   "customer_explanation", [item.id], "detect_structuring",
                                   "A regular business purpose would weaken the structuring hypothesis.",
                                   "could_support_alternative", item.refs))
        elif item.tool == "summarize_activity":
            drivers.append(_driver("Is a longer account history available as a baseline?",
                                   "account_history", [item.id], "summarize_activity",
                                   "The synthetic baseline is short.", "resolves_unknown", item.refs))
        elif item.tool == "detect_embedded_instructions":
            drivers.append(_driver("Can a clean copy be obtained directly from the issuing registry?",
                                   "document_provenance", [item.id], "detect_embedded_instructions",
                                   "Embedded instructions put the document's provenance in question.",
                                   "resolves_unknown", item.refs))
    for gap in report.get("gaps", []):
        tools = TOOL_FAMILIES.get(gap.get("role"), set())
        drivers.append(_driver(f"Re-run the {gap.get('role')} specialist; it did not complete.",
                               "rerun_specialist", [], max(tools, key=lambda t: TRIAGE_WEIGHTS.get(t, 0),
                                                           default=""),
                               "Missing specialist evidence leaves its typologies not evaluated.",
                               "resolves_unknown"))
    merged = {}
    for driver in drivers:
        key = (driver["question"], driver["request_type"])
        if key in merged:
            old = merged[key]
            driver = _driver(driver["question"], driver["request_type"],
                             old["affects_evidence_ids"] + driver["affects_evidence_ids"],
                             driver["_tool"], driver["rationale"], driver["effect"],
                             old["source_refs"] + driver["source_refs"])
        merged[key] = driver
    ranked = sorted(({k: v for k, v in d.items() if k != "_tool"} for d in merged.values()),
                    key=lambda d: (-d["impact_score"], d["id"]))
    return {"case_id": case.id, "drivers": ranked, "ranking_policy":
            "Triage weight of affected findings multiplied by their count (policy version 1).",
            "priority": follow_up_priority(evidence),
            "limitations": ["A ranking of what to ask next, not a probability that answers will "
                            "change the outcome."]}


def _check(evidence_id, alternative, status, facts, refs, note):
    return {"evidence_id": evidence_id, "alternative": alternative, "status": status,
            "facts": facts, "source_refs": sorted(set(refs)), "note": note}


def alternative_checks(case: Case, report: dict) -> dict:
    """Test the most common legitimate explanation for each indicator against the snapshot."""
    evidence = _evidence(report)
    txs = {t.id: t for t in case.transactions}
    entities = {e.id: e for e in case.entities}
    watch = {w.id: w for w in case.watchlist}
    checks = []
    for item in evidence:
        if item.claim_kind != "indicator":
            continue
        if item.tool in ("trace_flows", "detect_cycles"):
            path = [txs[i] for i in item.ordered_transaction_ids or [] if i in txs]
            if not path:
                continue
            pairs = {(t.sender, t.receiver) for t in path}
            prior = [t for t in case.transactions if (t.sender, t.receiver) in pairs
                     and t.timestamp < path[0].timestamp and t.id not in {p.id for p in path}]
            checks.append(_check(item.id, "Recurring commercial settlement between the same accounts",
                                 "supports_alternative" if prior else "does_not_support",
                                 {"prior_same_pair_transactions": len(prior),
                                  "path_pairs": len(pairs)},
                                 [t.id for t in prior] + [t.id for t in path],
                                 "Prior same-direction history is consistent with an established relationship."))
        elif item.tool == "detect_structuring":
            sender = item.payload.get("sender")
            flagged = set(item.refs)
            threshold = Decimal(str(item.parameters.get("threshold", "5000")))
            outside = [t for t in case.transactions if t.sender == sender and t.id not in flagged
                       and t.amount < threshold]
            receivers = {txs[i].receiver for i in flagged if i in txs}
            checks.append(_check(item.id, "Routine small payments such as payroll or supplier runs",
                                 "supports_alternative" if outside and len(receivers) > 1
                                 else "does_not_support",
                                 {"other_sub_threshold_payments": len(outside),
                                  "distinct_receivers_in_series": len(receivers)},
                                 [t.id for t in outside] + sorted(flagged),
                                 "Many receivers and a regular history fit routine disbursements better."))
        elif item.tool == "summarize_activity":
            target = txs.get(item.target_transaction_id or "")
            if not target:
                continue
            earlier = [t for t in case.transactions if t.sender == target.sender
                       and t.receiver == target.receiver and t.timestamp < target.timestamp]
            checks.append(_check(item.id, "Known counterparty receiving a one-off large payment",
                                 "supports_alternative" if earlier else "does_not_support",
                                 {"earlier_payments_to_same_receiver": len(earlier)},
                                 [t.id for t in earlier] + [target.id],
                                 "An existing counterparty relationship makes a one-off purchase more plausible."))
        elif item.tool == "compare_ownership_declaration":
            checks.append(_check(item.id, "Declaration predates a later ownership change",
                                 "not_evaluable", {}, item.refs,
                                 "Relationship and declaration dates are not supplied."))
        elif item.tool == "screen_candidates":
            entity = entities.get(item.payload.get("entity_id"))
            record = watch.get(item.payload.get("watchlist_id"))
            matched = item.payload.get("matched_identifiers", [])
            conflicts = item.payload.get("conflicting_identifiers", [])
            missing = sorted(set(entity.identifiers if entity else {})
                             ^ set(record.identifiers if record else {}))
            checks.append(_check(item.id, "A different person who shares the name",
                                 "does_not_support" if matched and not conflicts
                                 else "supports_alternative" if conflicts else "not_evaluable",
                                 {"matched_identifiers": len(matched),
                                  "conflicting_identifiers": len(conflicts),
                                  "identifiers_missing_on_one_side": len(missing)},
                                 item.refs, "Only identifier agreement can exclude a namesake."))
        elif item.tool == "compare_fields":
            declared, extracted = item.payload.get("declared"), item.payload.get("extracted")
            values = item.payload.get("values") or [declared, extracted]
            values = [v for v in values if isinstance(v, str)]
            if len(values) < 2:
                continue
            similarity = SequenceMatcher(None, normalize(values[0]), normalize(values[1])).ratio()
            checks.append(_check(item.id, "Transcription error or registry formatting difference",
                                 "supports_alternative" if similarity >= 0.8 else "does_not_support",
                                 {"value_similarity": round(similarity, 4)}, item.refs,
                                 "Near-identical values suggest a typo rather than a different record."))
    return {"case_id": case.id, "checks": checks, "check_version": 1,
            "limitations": ["Checks test one common legitimate explanation each; passing or "
                            "failing a check does not settle the case."]}


class GraphQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_id: str = Field(min_length=1, max_length=200)
    end_id: str | None = Field(default=None, max_length=200)
    max_hops: int = Field(default=3, ge=1, le=4)
    currency: str | None = Field(default=None, max_length=8)
    min_amount: str | None = Field(default=None, max_length=32)
    window_hours: int | None = Field(default=None, ge=1, le=720)
    chronological: bool = True

    @field_validator("min_amount")
    @classmethod
    def decimal_amount(cls, value):
        if value is None:
            return value
        try:
            if Decimal(value) < 0:
                raise ValueError("Minimum amount must not be negative")
        except InvalidOperation as exc:
            raise ValueError("Minimum amount must be a decimal string") from exc
        return value


def _accounts_for(case: Case, record_id: str | None) -> set[str]:
    if record_id is None:
        return set()
    accounts = {a.id for a in case.accounts}
    if record_id in accounts:
        return {record_id}
    owned = {a.id for a in case.accounts if a.entity_id == record_id}
    if not owned:
        raise ValueError("Query endpoint is not an account or account-holding entity in this case")
    return owned


def run_graph_query(case: Case, query: GraphQuery, max_paths=200, max_expansions=5000) -> dict:
    starts, ends = _accounts_for(case, query.start_id), _accounts_for(case, query.end_id)
    minimum = Decimal(query.min_amount) if query.min_amount else None
    outgoing = defaultdict(list)
    for tx in sorted(case.transactions, key=lambda t: (t.timestamp, t.id)):
        if (query.currency is None or tx.currency == query.currency) and (
                minimum is None or tx.amount >= minimum):
            outgoing[tx.sender].append(tx)
    paths, expansions, truncated = [], 0, False

    def walk(path, visited):
        nonlocal expansions, truncated
        expansions += 1
        if expansions > max_expansions or len(paths) >= max_paths:
            truncated = True
            return
        last = path[-1]
        if not ends or last.receiver in ends:
            hours = (last.timestamp - path[0].timestamp).total_seconds() / 3600
            paths.append({"ordered_transaction_ids": [t.id for t in path],
                          "accounts": [path[0].sender] + [t.receiver for t in path],
                          "amounts": [str(t.amount) for t in path],
                          "currencies": sorted({t.currency for t in path}),
                          "elapsed_hours": round(hours, 2), "hops": len(path)})
        if len(path) >= query.max_hops:
            return
        for nxt in outgoing[last.receiver]:
            if nxt.receiver in visited:
                continue
            if query.chronological and nxt.timestamp <= last.timestamp:
                continue
            if query.window_hours and (nxt.timestamp - path[0].timestamp).total_seconds() > \
                    query.window_hours * 3600:
                continue
            walk(path + [nxt], visited | {nxt.receiver})

    for start in sorted(starts):
        for tx in outgoing[start]:
            walk([tx], {start, tx.receiver})
    return {"case_id": case.id, "query": query.model_dump(), "paths": paths,
            "path_count": len(paths), "truncated": truncated,
            "limits": {"max_paths": max_paths, "max_expansions": max_expansions},
            "limitations": ["A connected path does not prove that the same funds moved.",
                            "Results are computed from the pinned snapshot; the query is not "
                            "added to the report."]}

