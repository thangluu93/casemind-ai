"""Read-only explorer projections from one verified case snapshot."""
from copy import deepcopy
from decimal import Decimal, localcontext
from datetime import datetime

from .analytics import normalize
from .models import Case
from .workspace import bounded_limit, evidence_for, scope_for, snapshot_metadata


def build_money_trail(case: Case, report=None, snapshot=None, *, account_id=None,
                      currency=None, direction="all", limit=200, start=None, end=None,
                      from_timestamp=None, to_timestamp=None) -> dict:
    limit = bounded_limit(limit)
    def parse_timestamp(value):
        if value is None:
            return None
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
        if not isinstance(parsed, datetime) or parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Display timestamps require an ISO timestamp with timezone")
        return parsed
    if start is not None and from_timestamp is not None or end is not None and to_timestamp is not None:
        raise ValueError("Supply only one form of each time bound")
    start = parse_timestamp(from_timestamp if from_timestamp is not None else start)
    end = parse_timestamp(to_timestamp if to_timestamp is not None else end)
    scope = scope_for(case, report, snapshot)
    accounts = {a.id: a for a in case.accounts}
    if account_id and account_id not in accounts:
        raise ValueError("Unknown scoped account")
    if direction not in {"all", "incoming", "outgoing"}:
        raise ValueError("Invalid direction")
    if direction != "all" and not account_id:
        raise ValueError("Direction filter requires an account")
    if start and end and start > end:
        raise ValueError("Invalid time window")
    evidence = evidence_for(case, report, snapshot)
    selected = []
    for tx in sorted(case.transactions, key=lambda tx: (tx.timestamp, tx.id)):
        if currency and tx.currency != currency:
            continue
        if account_id and account_id not in (tx.sender, tx.receiver):
            continue
        if account_id and direction == "incoming" and tx.receiver != account_id:
            continue
        if account_id and direction == "outgoing" and tx.sender != account_id:
            continue
        if (start and tx.timestamp < start) or (end and tx.timestamp > end):
            continue
        roles = [{"evidence_id": e.id, "role":
                  (e.participant_roles or {}).get(tx.id, "unknown")}
                 for e in evidence if tx.id in e.refs]
        selected.append({"id": tx.id, "display_key": tx.id, "sender": tx.sender,
                         "receiver": tx.receiver, "sender_entity_id": accounts[tx.sender].entity_id,
                         "receiver_entity_id": accounts[tx.receiver].entity_id,
                         "amount": str(tx.amount), "currency": tx.currency,
                         "timestamp": tx.timestamp.isoformat(), "participant_roles": roles})
    paths = []
    for e in evidence:
        if e.tool not in {"trace_flows", "detect_cycles"} or e.payload.get("truncated"):
            continue
        ordered = e.ordered_transaction_ids
        if ordered is None:
            # Legacy refs are a set; reconstruct traversal from source timestamps.
            ordered = [tx.id for tx in sorted(case.transactions, key=lambda tx: (tx.timestamp, tx.id))
                       if tx.id in e.refs]
        if not set(ordered) <= {tx.id for tx in case.transactions}:
            raise ValueError("Foreign transaction in path")
        paths.append({"evidence_id": e.id, "ordered_transaction_ids": ordered,
                      "order_status": "recorded" if e.ordered_transaction_ids is not None else "reconstructed_from_sources",
                      "parameters": e.parameters, "limitations": e.limitations})
    return {"version": 1, "scope": scope.model_dump(mode="json"),
            "transactions": selected[:limit], "paths": paths[:limit],
            "filters": {"account_id": account_id, "currency": currency, "direction": direction,
                        "start": start.isoformat() if start else None,
                        "end": end.isoformat() if end else None,
                        "from_timestamp": start.isoformat() if start else None,
                        "to_timestamp": end.isoformat() if end else None},
            "coverage": {"total": len(case.transactions), "matched": len(selected),
                         "visible": min(len(selected), limit),
                         "hidden": max(0, len(selected)-limit),
                         "hidden_paths": max(0, len(paths)-limit),
                         "state": "run_evidence" if report else "not_evaluated",
                         "limitations": ["Display filters do not recompute findings.",
                                          "Currencies are not combined.",
                                          "Temporal order does not prove shared funds."]}}


def build_ownership(case: Case, report=None, snapshot=None, *, target_id=None, limit=200) -> dict:
    limit = bounded_limit(limit)
    scope = scope_for(case, report, snapshot)
    entities = {e.id: e for e in case.entities}
    if target_id and target_id not in entities:
        raise ValueError("Unknown scoped target")
    parents = {}
    for relationship in case.relationships:
        parents.setdefault(relationship.owned, []).append(relationship)
    paths = []
    inspected = 0
    truncated = False

    def walk(target, current, chain, visited):
        nonlocal inspected, truncated
        for rel in parents.get(current, []):
            inspected += 1
            if inspected > 2000 or len(paths) >= 500:
                truncated = True
                return
            steps = chain + [rel]
            cycle = rel.owner in visited
            depth = len(steps) > 8
            terminal = entities[rel.owner].kind == "person" or cycle or depth
            if terminal or not parents.get(rel.owner):
                unknown = any(r.percentage is None for r in steps)
                with localcontext() as ctx:
                    ctx.prec = max(100, sum(len(str(r.percentage)) for r in steps) + 10)
                    product = Decimal(100)
                    for r in steps:
                        if r.percentage is not None:
                            product *= r.percentage / 100
                paths.append({"id": "/".join([target] + [r.id for r in steps]),
                              "target": target, "candidate": rel.owner,
                              "ordered_relationship_ids": [r.id for r in steps],
                              "steps": [{"id": r.id, "owner": r.owner, "owned": r.owned,
                                         "percentage": str(r.percentage)
                                         if r.percentage is not None else None} for r in steps],
                              "effective_percentage": None if unknown or cycle or depth else str(product),
                              "flags": {"unknown_percentage": unknown, "cycle": cycle,
                                        "depth_limit": depth, "overlap": False,
                                        "missing_ownership": not terminal},
                              "declaration": {"source_id": target,
                                              "value": entities[target].identifiers.get("beneficial_owner")}})
            else:
                walk(target, rel.owner, steps, visited | {rel.owner})

    for target in ([target_id] if target_id else list(entities)):
        walk(target, target, [], {target})
    for path in paths:
        path["flags"]["overlap"] = any(
            other is not path and other["target"] == path["target"] and
            set(other["ordered_relationship_ids"]) & set(path["ordered_relationship_ids"])
            for other in paths)
    return {"version": 1, "scope": scope.model_dump(mode="json"), "paths": paths[:limit],
            "coverage": {"hidden": max(0, len(paths)-limit), "truncated": truncated,
                         "examined_relationships": min(inspected, 2000),
                         "relationships": len(case.relationships)},
            "limitations": ["Independent per-path products; overlapping paths are not summed.",
                            "Candidate ownership is not a jurisdictional UBO determination.",
                            "Absent ownership records do not prove absence of ownership."]}


def build_document_comparison(case: Case, report, snapshot=None, *, document_id=None,
                              limit=200) -> dict:
    limit = bounded_limit(limit)
    scope = scope_for(case, report, snapshot)
    docs = {d.id: d for d in case.documents}
    if document_id and document_id not in docs:
        raise ValueError("Unknown scoped document")
    evidence = evidence_for(case, report, snapshot)
    extractions = [e for e in evidence if e.tool == "extract_document"]
    values = []
    for e in extractions:
        doc_id = e.payload.get("document_id")
        if not doc_id:
            continue
        if doc_id not in docs or doc_id not in e.refs:
            raise ValueError("Extraction document does not resolve")
        if document_id and doc_id != document_id:
            continue
        for field in e.payload.get("fields", []):
            values.append({"evidence_id": e.id, "field_name": field["key"],
                           "raw_value": field["value"], "normalized_value": normalize(field["value"]),
                           "locator": {"document_id": doc_id,
                                       "source_object": deepcopy(snapshot_metadata(snapshot).get("source_objects", {}).get(doc_id)
                                                                 or e.payload.get("source_object")),
                                       "lineage": deepcopy(e.document_lineage),
                                       "page": field.get("page"),
                                       "text_anchor": deepcopy(field.get("anchors", [])),
                                       "confidence": field.get("confidence"),
                                       "geometry": deepcopy(field.get("geometry"))}})
    comparisons = []
    for e in evidence:
        if e.tool != "compare_fields" or (document_id and document_id not in e.refs):
            continue
        comparisons.append({"evidence_id": e.id, "refs": e.refs,
                            "payload": deepcopy(e.payload), "limitations": e.limitations,
                            "values": [v for v in values if v["locator"]["document_id"] in e.refs
                                       and (not e.payload.get("field_name") or
                                            "".join(c for c in normalize(v["field_name"]) if c.isalnum()) ==
                                            "".join(c for c in normalize(e.payload["field_name"]) if c.isalnum()))]})
    return {"version": 1, "scope": scope.model_dump(mode="json"),
            "documents": [d.model_dump(mode="json") for d in docs.values()
                          if not document_id or d.id == document_id][:limit],
            "values": values[:limit], "comparisons": comparisons[:limit],
            "coverage": {"hidden_values": max(0, len(values)-limit),
                         "hidden_comparisons": max(0, len(comparisons)-limit)},
            "limitations": ["Inspect OCR values against the original page.",
                            "Missing geometry uses page and excerpt fallback.",
                            "Missing original-object metadata is explicitly unavailable."]}
