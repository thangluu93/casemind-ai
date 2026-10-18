"""Preserve original measurements; disclose a synthetic gold-label omission separately."""

import argparse
import json
from collections import Counter
from pathlib import Path

from casemind.models import digest


def rescore(root: Path):
    rows = json.loads((root / "results.json").read_text())
    original = json.loads((root / "summary.json").read_text())
    totals, corrections = Counter(), []
    for row in rows:
        if "error" in row:
            totals["errors"] += 1
            continue
        truth = json.loads((root / "private-truth" / (row["case_id"] + ".json")).read_text())
        expected = set(truth["expected_labels"])
        if truth["scenario"] == "ownership" and not truth["control"]:
            case = json.loads((root / "runtime-inputs" / (row["case_id"] + ".json")).read_text())
            entities = {e["id"]: e for e in case["entities"]}
            discrepancy = any(
                doc["fields"].get("Beneficial Owner")
                and entities[doc["entity_id"]]["identifiers"].get("beneficial_owner")
                != doc["fields"]["Beneficial Owner"]
                for doc in case["documents"]
            )
            if discrepancy and "document_mismatch" not in expected:
                expected.add("document_mismatch")
                corrected = truth | {"expected_labels": sorted(expected)}
                corrections.append(
                    {
                        "case_id": row["case_id"],
                        "repeat": row["repeat"],
                        "original_truth_hash": digest(truth),
                        "corrected_truth_hash": digest(corrected),
                    }
                )
        predicted = set(row["predicted"])
        totals.update(
            tp=len(expected & predicted), fp=len(predicted - expected), fn=len(expected - predicted)
        )
    result = {
        "original_totals": original["totals"],
        "corrected_totals": dict(totals),
        "corrections": corrections,
        "reason": "Positive ownership sources also plant a document/declaration discrepancy; original gold omitted it.",
        "limitation": "Post-run construction correction, not an independent preregistered accuracy measurement. Original artifacts retained.",
    }
    (root / "label-construction-rescore.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "corrections"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    rescore(parser.parse_args().directory)
