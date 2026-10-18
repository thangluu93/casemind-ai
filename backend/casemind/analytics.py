import re
from collections import defaultdict
from decimal import Decimal
from difflib import SequenceMatcher
from statistics import median

from .models import Case, Evidence, digest


def evidence(
    case: Case,
    tool: str,
    refs: list[str],
    payload: dict,
    indicator=False,
    limitations=None,
    parameters=None,
) -> Evidence:
    original_refs = list(dict.fromkeys(refs))
    tx_ids = {t.id for t in case.transactions}
    ordered = [r for r in original_refs if r in tx_ids]
    target = payload.get("transaction_id") if tool == "summarize_activity" else None
    roles = {r: ("target" if r == target else "baseline_context" if target else
                  "pattern_member" if indicator else "context") for r in ordered}
    refs = sorted(set(refs))
    if not refs or not set(refs) <= set(case.sources):
        raise ValueError("Evidence must resolve to the current case")
    return Evidence(
        id="ev-" + digest([case.id, tool, 2, refs, payload, ordered, roles])[:20],
        case_id=case.id,
        tool=tool,
        tool_version=2,
        refs=refs,
        payload=payload,
        claim_kind="indicator" if indicator else "observation",
        limitations=limitations or [],
        parameters=parameters or {},
        ordered_transaction_ids=ordered,
        participant_roles=roles,
        target_transaction_id=target,
        coverage={"status": "partial" if payload.get("truncated") else "evaluated",
                  "transaction_count": len(case.transactions)},
        document_lineage=payload.get("document_lineage") or [{"document_id": r, "original_sha256": payload.get("pdf_hash"),
                           "original_generation": payload.get("original_generation"),
                           "fields": payload.get("fields", [])}
                          for r in refs if r in {d.id for d in case.documents}],
    )


def get_transactions(case: Case) -> list[Evidence]:
    return [
        evidence(
            case,
            "get_transactions",
            [t.id for t in case.transactions],
            {"transaction_count": len(case.transactions), "account_count": len(case.accounts)},
            limitations=["Synthetic, short history; no population baseline."],
        )
    ]


DEFAULT_RULES = {
    "flow_minimum_amount": Decimal("10000"),
    "flow_window_hours": 48,
    "flow_minimum_retained_ratio": Decimal("0.8"),
    "flow_maximum_retained_ratio": Decimal("1.05"),
    "structuring_threshold": Decimal("5000"),
    "structuring_window_hours": 24,
    "structuring_minimum_count": 3,
    "activity_median_multiple": 10,
}


def rules(overrides: dict | None = None) -> dict:
    """Demonstration rule parameters; overrides are used only for explicit what-if simulation."""
    return DEFAULT_RULES | (overrides or {})


def trace_flows(case: Case, params: dict | None = None) -> list[Evidence]:
    p = rules(params)
    low, high = p["flow_minimum_retained_ratio"], p["flow_maximum_retained_ratio"]
    outgoing = defaultdict(list)
    for tx in sorted(case.transactions, key=lambda t: (t.timestamp, t.id)):
        outgoing[tx.sender].append(tx)
    findings = []
    inspected = 0
    truncated = False

    def walk(path, visited):
        nonlocal inspected, truncated
        inspected += 1
        if inspected > 2000 or len(findings) >= 40:
            truncated = True
            return
        first, last = path[0], path[-1]
        ratio = last.amount / first.amount
        hours = (last.timestamp - first.timestamp).total_seconds() / 3600
        if len(path) >= 2 and not low <= ratio <= high:
            return
        payload = {
            "accounts": [first.sender] + [t.receiver for t in path],
            "amounts": [str(t.amount) for t in path],
            "currency": first.currency,
            "hours": hours,
            "retained_ratio": str(ratio),
        }
        parameters = {
            "window_hours": p["flow_window_hours"],
            "max_hops": 4,
            "minimum_amount": str(p["flow_minimum_amount"]),
            "minimum_retained_ratio": str(low),
            "maximum_retained_ratio": str(high),
        }
        if last.receiver == first.sender:
            if len(path) >= 3 and low <= ratio <= high:
                findings.append(
                    evidence(
                        case,
                        "detect_cycles",
                        [t.id for t in path],
                        payload,
                        True,
                        ["Temporal sequence does not prove shared funds or intent."],
                        parameters,
                    )
                )
            return
        if len(path) >= 2 and low <= ratio <= high:
            findings.append(
                evidence(
                    case,
                    "trace_flows",
                    [t.id for t in path],
                    payload,
                    True,
                    ["Legitimate settlements can show this pattern."],
                    parameters,
                )
            )
        if len(path) >= 4 or last.receiver in visited:
            return
        for nxt in outgoing[last.receiver]:
            if (
                nxt.currency == first.currency
                and last.timestamp < nxt.timestamp
                and (nxt.timestamp - first.timestamp).total_seconds() <= p["flow_window_hours"] * 3600
            ):
                walk(path + [nxt], visited | {last.receiver})

    for tx in case.transactions:
        if tx.amount >= p["flow_minimum_amount"]:
            walk([tx], {tx.sender})
    if truncated:
        findings.append(
            evidence(
                case,
                "trace_flows",
                [t.id for t in case.transactions],
                {"truncated": True, "examined_paths": min(inspected, 2000)},
                limitations=["Path search reached its result or work cap."],
            )
        )
    return findings


def detect_structuring(case: Case, params: dict | None = None) -> list[Evidence]:
    p = rules(params)
    threshold, window_seconds = p["structuring_threshold"], p["structuring_window_hours"] * 3600
    groups = defaultdict(list)
    for tx in case.transactions:
        if tx.amount < threshold:
            groups[(tx.sender, tx.currency)].append(tx)
    findings = []
    for (sender, currency), transactions in groups.items():
        transactions.sort(key=lambda t: (t.timestamp, t.id))
        for first in transactions:
            window = [
                t
                for t in transactions
                if 0 <= (t.timestamp - first.timestamp).total_seconds() <= window_seconds
            ]
            total = sum((t.amount for t in window), Decimal(0))
            if len(window) >= p["structuring_minimum_count"] and total > threshold:
                findings.append(
                    evidence(
                        case,
                        "detect_structuring",
                        [t.id for t in window],
                        {
                            "sender": sender,
                            "count": len(window),
                            "total": str(total),
                            "currency": currency,
                        },
                        True,
                        [f"{threshold} is a demonstration rule, not a legal reporting threshold."],
                        {"threshold": str(threshold), "window_hours": p["structuring_window_hours"],
                         "minimum_count": p["structuring_minimum_count"]},
                    )
                )
                break
    return findings


def summarize_activity(case: Case, params: dict | None = None) -> list[Evidence]:
    multiple = rules(params)["activity_median_multiple"]
    groups = defaultdict(list)
    for tx in case.transactions:
        groups[(tx.sender, tx.currency)].append(tx)
    findings = []
    for (sender, currency), txs in groups.items():
        if len(txs) < 8:
            continue
        typical = median(t.amount for t in txs)
        for tx in txs:
            if tx.amount >= typical * multiple:
                findings.append(
                    evidence(
                        case,
                        "summarize_activity",
                        [t.id for t in txs],
                        {
                            "sender": sender,
                            "amount": str(tx.amount),
                            "median": str(typical),
                            "transaction_id": tx.id,
                            "currency": currency,
                        },
                        True,
                        ["Small synthetic baseline; contextual review required."],
                        {"median_multiple": multiple},
                    )
                )
    return findings


def transaction_analysis(case: Case) -> list[Evidence]:
    findings = (get_transactions(case) + trace_flows(case)
                + detect_structuring(case) + summarize_activity(case))
    truncated = any(e.payload.get("truncated") for e in findings)
    findings[0].coverage = {"status": "partial" if truncated else "evaluated",
                           "transaction_count": len(case.transactions),
                           "evaluated_tools": ["trace_flows", "detect_cycles",
                                               "detect_structuring", "summarize_activity"]}
    return findings


def normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def entity_analysis(case: Case) -> list[Evidence]:
    parents = defaultdict(list)
    entities = {e.id: e for e in case.entities}
    for rel in case.relationships:
        parents[rel.owned].append(rel)
    findings = []

    def walk(target, current, share, path, visited):
        for rel in parents[current]:
            refs = [r.id for r in path + [rel]] + [target, rel.owner]
            chain = path + [rel]
            if rel.owner in visited or len(chain) > 8:
                findings.append(
                    evidence(
                        case,
                        "trace_ownership",
                        refs,
                        {"target": target, "status": "unresolved_cycle_or_depth"},
                    )
                )
                continue
            effective = (
                None if share is None or rel.percentage is None else share * rel.percentage / 100
            )
            if entities[rel.owner].kind == "person":
                findings.append(
                    evidence(
                        case,
                        "trace_ownership",
                        refs,
                        {
                            "target": target,
                            "candidate": rel.owner,
                            "effective_percentage": str(effective)
                            if effective is not None
                            else None,
                            "path": [r.id for r in chain],
                            "status": "candidate_requires_review",
                        },
                        effective is not None and effective >= 25,
                        [
                            "Per-path multiplication only; no aggregation or legal UBO determination."
                        ],
                        {"max_depth": 8, "demo_candidate_threshold": "25"},
                    )
                )
                declared = entities[target].identifiers.get("beneficial_owner")
                if (
                    effective is not None
                    and effective >= 25
                    and declared
                    and normalize(declared) != normalize(entities[rel.owner].name)
                ):
                    findings.append(
                        evidence(
                            case,
                            "compare_ownership_declaration",
                            refs,
                            {
                                "target": target,
                                "declared_owner_name": declared,
                                "traced_candidate": rel.owner,
                                "candidate_name": entities[rel.owner].name,
                                "effective_percentage": str(effective),
                                "path": [r.id for r in chain],
                                "status": "declaration_discrepancy_requires_review",
                            },
                            True,
                            ["A declaration discrepancy is not proof of concealment or intent."],
                        )
                    )
            else:
                walk(target, rel.owner, effective, chain, visited | {rel.owner})

    for entity in case.entities:
        walk(entity.id, entity.id, Decimal(100), [], {entity.id})
    for index, first in enumerate(case.entities):
        for second in case.entities[index + 1 :]:
            similarity = SequenceMatcher(
                None, normalize(first.name), normalize(second.name)
            ).ratio()
            if first.kind == second.kind and similarity >= 0.85:
                findings.append(
                    evidence(
                        case,
                        "resolve_candidates",
                        [first.id, second.id],
                        {"name_similarity": similarity, "merged": False},
                        limitations=["Similar names never automatically merge identities."],
                    )
                )
    if not findings:
        findings.append(
            evidence(
                case,
                "get_relationships",
                [e.id for e in case.entities],
                {"relationship_count": len(case.relationships)},
                limitations=["No ownership links does not prove absence of ownership."],
            )
        )
    return findings


def screening_analysis(case: Case) -> list[Evidence]:
    findings = []
    for entity in case.entities:
        for record in case.watchlist:
            similarity = SequenceMatcher(
                None, normalize(entity.name), normalize(record.name)
            ).ratio()
            if similarity < 0.8:
                continue
            common = sorted(set(entity.identifiers) & set(record.identifiers))
            matches = [
                k
                for k in common
                if normalize(entity.identifiers[k]) == normalize(record.identifiers[k])
            ]
            conflicts = [k for k in common if k not in matches]
            status = (
                "likely_false_positive"
                if len(conflicts) >= 2 and not matches
                else ("potential_match" if matches and not conflicts else "inconclusive")
            )
            findings.append(
                evidence(
                    case,
                    "screen_candidates",
                    [entity.id, record.id],
                    {
                        "entity_id": entity.id,
                        "watchlist_id": record.id,
                        "category": record.category,
                        "name_similarity": similarity,
                        "matched_identifiers": matches,
                        "conflicting_identifiers": conflicts,
                        "status": status,
                    },
                    status == "potential_match",
                    ["Fictional list; all dispositions require human review."],
                )
            )
    if not findings:
        findings.append(
            evidence(
                case,
                "screen_candidates",
                [e.id for e in case.entities],
                {"candidate_count": 0, "list_count": len(case.watchlist)},
                limitations=["No candidate in this supplied list is not a clearance."],
            )
        )
    return findings


EMBEDDED_INSTRUCTION_PATTERNS = {
    "override_instructions": r"\b(?:ignore|disregard|forget)\b.{0,40}\b(?:instructions?|rules|prompts?)\b",
    "role_reassignment": r"\b(?:system prompt|system override|you are now|act as)\b",
    "disposition_command": r"\b(?:approve|clear|close|dismiss)\b.{0,30}\b(?:case|customer|alert|review)\b"
                           r"|\bmark\b.{0,40}\bcleared\b",
    "suppress_reporting": r"\bdo not (?:report|flag|escalate|review)\b",
}
WITHHELD = "[withheld from model context: embedded instruction text]"


def embedded_instruction_matches(text: str) -> list[str]:
    lowered = normalize(text)
    return [name for name, pattern in EMBEDDED_INSTRUCTION_PATTERNS.items()
            if re.search(pattern, lowered)]


def redact_untrusted(value):
    """Copy a model-bound payload, replacing text that tries to direct the reader."""
    if isinstance(value, str):
        return WITHHELD if embedded_instruction_matches(value) else value
    if isinstance(value, list):
        return [redact_untrusted(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_untrusted(item) for key, item in value.items()}
    return value


def detect_embedded_instructions(case: Case, extracted: list[dict]) -> list[Evidence]:
    findings = []
    for item in extracted:
        matched_fields, patterns = [], set()
        for field in item.get("fields", []):
            found = embedded_instruction_matches(f"{field.get('key', '')} {field.get('value', '')}")
            if found:
                matched_fields.append(field.get("key"))
                patterns.update(found)
        text_patterns = embedded_instruction_matches(item.get("text") or "")
        patterns.update(text_patterns)
        if not patterns:
            continue
        findings.append(
            evidence(
                case,
                "detect_embedded_instructions",
                [item["document_id"]],
                {"document_id": item["document_id"], "field_keys": matched_fields,
                 "text_matched": bool(text_patterns), "patterns": sorted(patterns),
                 "status": "untrusted_instruction_withheld"},
                True,
                limitations=["Embedded text is untrusted data. It was withheld from model context "
                             "and neither clears nor implicates the subject; document provenance "
                             "needs review."],
                parameters={"pattern_set_version": 1},
            )
        )
    return findings


def compare_extracted(case: Case, extracted: list[dict]) -> list[Evidence]:
    findings = []
    entities = {e.id: e for e in case.entities}
    docs = {d.id: d for d in case.documents}
    seen = defaultdict(list)
    keys = {"registrationid": "registration_id", "beneficialowner": "beneficial_owner"}
    for item in extracted:
        doc = docs[item["document_id"]]
        findings.append(
            evidence(
                case,
                "extract_document",
                [doc.id],
                {k: v for k, v in item.items() if k in ("document_id", "original_generation", "snapshot_id", "pdf_hash", "processor", "fields", "page_count")},
                limitations=["OCR fields require inspection against the page. Full OCR remains in the scoped extraction artifact, outside report prose/export."],
            )
        )
        available = {
            "".join(c for c in normalize(f["key"]) if c.isalnum())
            for f in item["fields"]
            if f["confidence"] >= 0.7
        }
        missing = sorted(set(keys) - available)
        if missing:
            findings.append(
                evidence(
                    case,
                    "compare_fields",
                    [doc.id],
                    {"status": "unresolved_missing_fields", "fields": missing},
                    limitations=["Required labels were not extracted confidently."],
                )
            )
        for field in item["fields"]:
            key = keys.get("".join(c for c in normalize(field["key"]) if c.isalnum()))
            if not key:
                continue
            if field["confidence"] < 0.7:
                findings.append(
                    evidence(
                        case,
                        "compare_fields",
                        [doc.id],
                        {"status": "unresolved_low_confidence", "field": field},
                    )
                )
                continue
            value = normalize(field["value"])
            expected = entities[doc.entity_id].identifiers.get(key)
            if expected is not None and normalize(expected) != value:
                findings.append(
                    evidence(
                        case,
                        "compare_fields",
                        [doc.id, doc.entity_id],
                        {
                            "status": "declared_field_mismatch",
                            "field_name": key,
                            "extracted": field["value"],
                            "declared": expected,
                            "page": field["page"],
                            "anchors": field["anchors"],
                            "pdf_hash": item.get("pdf_hash"),
                            "original_generation": item.get("original_generation"),
                            "fields": [field],
                        },
                        True,
                    )
                )
            seen[(doc.entity_id, key)].append((doc.id, value, {
                "document_id": doc.id, "original_sha256": item.get("pdf_hash"),
                "original_generation": item.get("original_generation"), "fields": [field]}))
    for (entity_id, key), values in seen.items():
        if len({value for _, value, _ in values}) > 1:
            findings.append(
                evidence(
                    case,
                    "compare_fields",
                    [doc_id for doc_id, _, _ in values] + [entity_id],
                    {
                        "status": "cross_document_mismatch",
                        "field_name": key,
                        "values": [value for _, value, _ in values],
                        "document_lineage": [lineage for _, _, lineage in values],
                    },
                    True,
                )
            )
    findings.extend(detect_embedded_instructions(case, extracted))
    if not case.documents:
        findings.append(
            evidence(
                case,
                "extract_document",
                [e.id for e in case.entities],
                {"document_count": 0},
                limitations=["No KYC/KYB documents supplied."],
            )
        )
    return findings
