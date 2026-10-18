"""Evaluator-only labels. This directory is excluded from cloud source and images."""

import argparse
import asyncio
import json
import os
import time
from collections import Counter
from pathlib import Path
from uuid import uuid4

from casemind.analytics import (
    compare_extracted,
    entity_analysis,
    screening_analysis,
    transaction_analysis,
)
from casemind.case_resolver import demo_snapshot, CaseResolver
from casemind.generator import SCENARIOS, generate_case
from casemind.models import digest


def expected_labels(scenario, control):
    if control:
        return set()
    return {
        "layering": {"rapid_flow", "structuring", "ownership_candidate"},
        "circular": {"rapid_flow", "cycle"},
        "ownership": {"ownership_candidate", "document_mismatch"},
        "screening": {"potential_watchlist_match"},
        "documents": {"document_mismatch"},
    }[scenario]


def observed_labels(evidence):
    labels = set()
    mapping = {
        "trace_flows": "rapid_flow",
        "detect_cycles": "cycle",
        "detect_structuring": "structuring",
        "trace_ownership": "ownership_candidate",
        "screen_candidates": "potential_watchlist_match",
        "compare_fields": "document_mismatch",
    }
    for item in evidence:
        if item["claim_kind"] == "indicator" and item["tool"] in mapping:
            labels.add(mapping[item["tool"]])
    return labels


def corpus():
    for scenario in SCENARIOS:
        for index in range(10):
            seed = 1000 + index
            control = index % 2 == 1
            case = generate_case(scenario, seed, control)
            yield (
                case,
                {
                    "case_id": case.id,
                    "scenario": scenario,
                    "control": control,
                    "expected_labels": sorted(expected_labels(scenario, control)),
                    "split": "development" if index < 4 else "held-out",
                },
            )


def offline_extractions(case):
    """Evaluator-only labelled adapter; this does not measure OCR quality."""
    return [{"document_id": doc.id, "adapter": "offline-synthetic-fields-v1",
             "fields": [{"key": key, "value": value, "confidence": 1.0,
                         "page": 1, "anchors": {"key": [], "value": []}}
                        for key, value in doc.fields.items()],
             "text": "", "page_count": 1} for doc in case.documents]


async def main(args):
    cloud = None
    config = {"mode": "offline", "extraction_adapter": "offline-synthetic-fields-v1"}
    if args.live:
        from casemind.cloud import Cloud
        from casemind.investigation import investigate
        config = json.loads(Path("artifacts/cloud-config.json").read_text())
        os.environ["CASEMIND_PROCESSOR"] = config["processor"]
        cloud = Cloud()
    output = Path("evaluation-output") / ("run-" + time.strftime("%Y%m%d-%H%M%S"))
    (output / "runtime-inputs").mkdir(parents=True)
    (output / "private-truth").mkdir(mode=0o700)
    mode = "live" if args.live else "offline"
    configuration_hash = digest(config)
    evaluated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    source_hash_at_start = digest(
        {p.name: p.read_text() for p in Path("backend/casemind").glob("*.py")}
    )
    (output / "source-freeze.json").write_text(
        json.dumps({"source_hash_at_start": source_hash_at_start, "configuration_hash": configuration_hash, "mode": mode, "evaluated_at": evaluated_at})
    )
    selected = [
        (c, truth) for c, truth in corpus() if args.split == "all" or truth["split"] == args.split
    ]
    manifest = []
    for case, truth in selected:
        (output / "runtime-inputs" / (case.id + ".json")).write_text(case.model_dump_json())
        (output / "private-truth" / (case.id + ".json")).write_text(json.dumps(truth))
        manifest.append(
            {"case_id": case.id, "input_hash": digest(case), "truth_hash": digest(truth)}
        )
    (output / "frozen-manifest.json").write_text(json.dumps(manifest, indent=2))
    totals = Counter()
    results = []
    semaphore = asyncio.Semaphore(args.concurrency)

    async def evaluate(case, truth, repeat):
        async with semaphore:
            started = time.monotonic()
            run_id = "eval-" + uuid4().hex[:20]
            try:
                if args.live:
                    snapshot = demo_snapshot(case)
                    documents = {d.id: CaseResolver(cloud.store, {}).document_bytes(snapshot, d.id) for d in case.documents}
                    await asyncio.to_thread(cloud.load_case, snapshot, documents)
                    cloud.ledger.reserve_run(output.name + "-evaluation-" + case.id, run_id)
                    events = []

                    async def emit(role, status, payload=None):
                        events.append({"role": role, "status": status, "payload": payload or {}})

                    report = await investigate(demo_snapshot(case), run_id, cloud.store, cloud, emit)
                    evidence = report["evidence"]
                    citations_valid = all(
                        set(c["evidence_ids"]) <= {e["id"] for e in evidence}
                        for c in report["synthesis"]["hypotheses"]
                    )
                    (output / (run_id + ".json")).write_text(
                        json.dumps({"report": report, "events": events}, indent=2)
                    )
                    gaps = report["gaps"]
                    usage = report["usage"]
                else:
                    extracted = offline_extractions(case)
                    records = (
                        transaction_analysis(case)
                        + entity_analysis(case)
                        + screening_analysis(case)
                        + compare_extracted(case, extracted)
                    )
                    evidence = [e.model_dump(mode="json") for e in records]
                    citations_valid, gaps, usage = True, [], {}
                predicted = observed_labels(evidence)
                expected = set(truth["expected_labels"])
                counts = {
                    "tp": len(expected & predicted),
                    "fp": len(predicted - expected),
                    "fn": len(expected - predicted),
                }
                totals.update(counts)
                sources_valid = all(
                    set(e["refs"]) <= set(case.sources) and e["case_id"] == case.id
                    for e in evidence
                )
                result = {
                    "case_id": case.id,
                    "repeat": repeat,
                    "expected": sorted(expected),
                    "predicted": sorted(predicted),
                    **counts,
                    "citation_scope_valid": citations_valid,
                    "source_scope_valid": sources_valid,
                    "gaps": gaps,
                    "usage": usage,
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                }
            except Exception as exc:
                totals["errors"] += 1
                result = {
                    "case_id": case.id,
                    "repeat": repeat,
                    "error": type(exc).__name__,
                    "message": str(exc)[:200],
                }
            results.append(result)
            (output / "results.json").write_text(json.dumps(results, indent=2))
            print(json.dumps(result), flush=True)

    await asyncio.gather(
        *(
            evaluate(case, truth, repeat)
            for case, truth in selected
            for repeat in range(args.repeats)
        )
    )
    summary = {
        "split": args.split,
        "live": args.live,
        "mode": mode,
        "evaluated_at": evaluated_at,
        "configuration_hash": configuration_hash,
        "extraction_quality_measured": args.live,
        "case_count": len(selected),
        "repeats": args.repeats,
        "totals": dict(totals),
        "source_hash_at_start": source_hash_at_start,
        "disk_source_hash_at_finish": digest(
            {p.name: p.read_text() for p in Path("backend/casemind").glob("*.py")}
        ),
        "scope": "Template-generated synthetic benchmark; not evidence of real-world AML accuracy.",
        "synthesis_semantic_support": "Requires human review; citation membership is not proof of semantic support.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print("OUTPUT", output, json.dumps(summary), flush=True)
    return output, summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["all", "development", "held-out"], default="all")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--repeats", type=int, choices=[1, 2, 3], default=1)
    parser.add_argument("--concurrency", type=int, choices=[1, 2, 3], default=1)
    asyncio.run(main(parser.parse_args()))
