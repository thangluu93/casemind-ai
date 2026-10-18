from .models import Evidence


def follow_up_priority(evidence: list[Evidence]) -> dict:
    """Explicit demonstration triage policy; never a probability of crime."""
    weights = {
        "trace_flows": 10,
        "detect_cycles": 25,
        "detect_structuring": 20,
        "compare_ownership_declaration": 20,
        "screen_candidates": 25,
        "compare_fields": 20,
        "detect_embedded_instructions": 20,
    }
    contributors = [
        {
            "tool": tool,
            "weight": weight,
            "evidence_ids": [
                e.id for e in evidence if e.tool == tool and e.claim_kind == "indicator"
            ],
        }
        for tool, weight in weights.items()
    ]
    contributors = [c for c in contributors if c["evidence_ids"]]
    score = min(100, sum(c["weight"] for c in contributors))
    return {
        "score": score,
        "level": "follow_up" if score >= 20 else "routine_review",
        "contributors": contributors,
        "policy_version": 2,
        "interpretation": "Demonstration triage score, not a probability or finding of criminality.",
    }
