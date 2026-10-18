"""Write an aggregate-only evaluation scorecard for the workspace.

Reads evaluator output under evaluation-output/ and emits counts and rates only.
Per-case expected labels, private truth and runtime inputs are never copied.
Run from the repository root: ./.venv/bin/python scripts/build-evaluation-summary.py
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path("evaluation-output")
TARGET = Path("backend/casemind/data/evaluation-summary.json")


def rate(numerator, denominator):
    return None if not denominator else round(numerator / denominator, 4)


def summarize(run_dir: Path) -> dict | None:
    summary_path, results_path = run_dir / "summary.json", run_dir / "results.json"
    if not summary_path.exists() or not results_path.exists():
        return None
    summary = json.loads(summary_path.read_text())
    results = json.loads(results_path.read_text())
    completed = [r for r in results if "error" not in r]
    errors = Counter(r["error"] for r in results if "error" in r)
    tp, fp, fn = (sum(r.get(k, 0) for r in completed) for k in ("tp", "fp", "fn"))
    controls = [r for r in completed if not r.get("expected")]
    usage = [r["usage"] for r in completed if r.get("usage", {}).get("model_calls")]
    elapsed = [r["elapsed_seconds"] for r in completed if r.get("elapsed_seconds")]
    return {
        "run": run_dir.name,
        "mode": "live" if summary.get("live") else "offline",
        "split": summary.get("split"),
        "evaluated_at": summary.get("evaluated_at"),
        "run_started_local": "{}-{}-{} {}:{}".format(
            run_dir.name[4:8], run_dir.name[8:10], run_dir.name[10:12],
            run_dir.name[13:15], run_dir.name[15:17]),
        "source_code_hash": summary.get("source_code_hash") or summary.get("source_hash_at_start"),
        "case_count": summary.get("case_count"),
        "repeats": summary.get("repeats"),
        "attempts": len(results),
        "completed": len(completed),
        "errors": dict(sorted(errors.items())),
        "true_positive_labels": tp,
        "false_positive_labels": fp,
        "false_negative_labels": fn,
        "precision": rate(tp, tp + fp),
        "recall": rate(tp, tp + fn),
        "control_attempts": len(controls),
        "control_attempts_with_false_positive": sum(1 for r in controls if r.get("fp")),
        "citation_scope_valid_rate": rate(
            sum(1 for r in completed if r.get("citation_scope_valid")), len(completed)),
        "source_scope_valid_rate": rate(
            sum(1 for r in completed if r.get("source_scope_valid")), len(completed)),
        "attempts_with_gaps": sum(1 for r in completed if r.get("gaps")),
        "mean_model_calls": rate(sum(u["model_calls"] for u in usage), len(usage)),
        "mean_input_tokens": rate(sum(u.get("input_tokens", 0) for u in usage), len(usage)),
        "mean_output_tokens": rate(sum(u.get("output_tokens", 0) for u in usage), len(usage)),
        "mean_elapsed_seconds": rate(sum(elapsed), len(elapsed)),
        "extraction_quality_measured": summary.get("extraction_quality_measured", False),
        "scope": summary.get("scope"),
        "synthesis_semantic_support": summary.get("synthesis_semantic_support"),
    }


def main():
    runs = [s for d in sorted(ROOT.glob("run-*")) if (s := summarize(d))]
    latest = {}
    for item in runs:
        latest[item["mode"]] = item
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps({
        "generated_from": "evaluation-output aggregate summaries; no per-case labels",
        "latest": latest,
        "history": [{k: r[k] for k in ("run", "run_started_local", "mode", "split", "completed", "attempts",
                                        "precision", "recall")} for r in runs],
        "interpretation": "Template-generated synthetic benchmark. Not evidence of real-world "
                          "AML accuracy. Analytics label quality is measured separately from "
                          "model prose, whose semantic support requires human review.",
    }, indent=2) + "\n")
    print(f"Wrote {TARGET} from {len(runs)} runs")


if __name__ == "__main__":
    main()
