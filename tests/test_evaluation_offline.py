import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace


def test_full_offline_corpus_never_constructs_cloud_or_reads_cloud_config(tmp_path, monkeypatch):
    # Load the actual entrypoint before moving into an isolated output directory.
    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("casemind_offline_evaluation", repo / "evaluation/run-evaluation.py")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    import casemind.cloud
    def prohibited(*args, **kwargs):
        raise AssertionError("Offline evaluation attempted a cloud call")
    monkeypatch.setattr(casemind.cloud, "Cloud", prohibited)
    monkeypatch.setattr(casemind.cloud, "credentials", prohibited)
    monkeypatch.chdir(tmp_path)
    # Freeze source from the actual source tree, without a cloud-config file.
    (tmp_path / "backend").symlink_to(repo / "backend", target_is_directory=True)
    output, summary = asyncio.run(evaluator.main(SimpleNamespace(live=False, split="all", repeats=1, concurrency=1)))
    assert summary["case_count"] == 50
    assert summary["mode"] == "offline"
    assert not summary["extraction_quality_measured"]
    assert summary["totals"].get("errors", 0) == 0
    assert len(list((output / "private-truth").glob("*.json"))) == 50
    assert len(list((output / "runtime-inputs").glob("*.json"))) == 50
    for runtime in (output / "runtime-inputs").glob("*.json"):
        assert "expected_labels" not in runtime.read_text()
