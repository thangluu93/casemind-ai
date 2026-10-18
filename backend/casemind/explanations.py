"""Transaction attribution uses deterministic tool evidence, never model prose."""
from .models import Evidence, SnapshotRef


def build_transaction_reasons(snapshot: SnapshotRef, evidence: list[Evidence | dict], transaction_id: str) -> dict:
    tx = next((t for t in snapshot.case.transactions if t.id == transaction_id), None)
    if tx is None:
        raise KeyError(transaction_id)
    reasons, gaps = [], []
    evaluated = False
    for raw in evidence:
        ev = Evidence.model_validate(raw)
        if ev.case_id != snapshot.case.id:
            raise ValueError("Evidence outside snapshot")
        if transaction_id not in ev.refs:
            continue
        role = (ev.participant_roles or {}).get(transaction_id)
        if role is None:
            gaps.append("Legacy evidence has unknown participation and order")
            continue
        evaluated = evaluated or ((ev.coverage or {}).get("status") == "evaluated" and
                                   (ev.tool in ("trace_flows", "detect_cycles", "detect_structuring", "summarize_activity")
                                    or bool((ev.coverage or {}).get("evaluated_tools"))))
        if ev.claim_kind != "indicator" or role not in ("target", "pattern_member"):
            continue
        reasons.append({"evidence_id": ev.id, "rule": ev.tool, "version": ev.tool_version,
                        "parameters": ev.parameters, "role": role,
                        "observed_facts": ev.payload,
                        "ordered_transaction_ids": ev.ordered_transaction_ids,
                        "order_status": "known" if ev.ordered_transaction_ids is not None else "order_unknown",
                        "alternatives": ev.limitations,
                        "gaps": [] if (ev.coverage or {}).get("status") == "evaluated" else ["Partial tool coverage"]})
    return {"transaction_id": transaction_id, "snapshot_id": snapshot.snapshot_id,
            "observed_transaction": tx.model_dump(mode="json"), "reasons": reasons,
            "status": "indicator" if reasons else "no_indicator" if evaluated else "not_evaluated",
            "gaps": sorted(set(gaps)), "disposition": "human_review_required"}
