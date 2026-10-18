import html

import pytest

from casemind.analytics import transaction_analysis
from casemind.exports import build_export_view, render_html, render_pdf
from casemind.generator import generate_case
from casemind.models import digest
from test_workspace_api import make_report


def test_export_fact_parity_and_escaping_without_report_mutation():
    case = generate_case("circular")
    report = make_report(case, transaction_analysis(case))
    report["synthesis"]["summary"] = '<script>alert("x")</script> https://host.invalid/'
    report["hash"] = digest({k: v for k, v in report.items() if k != "hash"})
    original = digest(report)
    view = build_export_view(case, report)
    rendered = render_html(view)
    assert "<script>" not in rendered and "&lt;script&gt;" in rendered
    assert "<a " not in rendered and "<iframe" not in rendered
    assert report["hash"] in rendered and report["input_hash"] in rendered
    assert report["synthesis"]["summary"] in html.unescape(rendered)
    pdf = render_pdf(view)
    assert pdf.startswith(b"%PDF-")
    assert report["hash"].encode() in pdf and report["input_hash"].encode() in pdf
    assert b"/JavaScript" not in pdf and b"/URI" not in pdf
    assert digest(report) == original
    assert any("not embedded" in line for s in view.sections for line in s.lines)


def test_export_rejects_tampering_and_foreign_review():
    case = generate_case("circular")
    report = make_report(case, transaction_analysis(case))
    with pytest.raises(ValueError):
        build_export_view(case, {**report, "priority": "changed"})
    with pytest.raises(ValueError):
        build_export_view(case, report, review={"report_hash": "foreign"})


def test_readable_reasons_coverage_and_source_provenance_have_html_pdf_parity():
    import pypdfium2 as pdfium
    from casemind.case_resolver import create_manifest, snapshot_from_manifest
    from casemind.models import SourceObjectRef
    case = generate_case("circular")
    source_id = case.transactions[0].id
    ref = SourceObjectRef(sha256="a" * 64, media_type="text/csv", byte_size=512,
                          generation=7, storage_key="sources/csv-original")
    metadata = {source_id: {"classification": "synthetic", "origin": "uploaded",
                           "locator": "row/2", "source_object": ref.model_dump(mode="json")}}
    snapshot = snapshot_from_manifest(create_manifest(case, {}, metadata, owner_id="reviewer"))
    report = make_report(case, transaction_analysis(case))
    report["input_hash"] = snapshot.snapshot_id
    report["hash"] = digest({k: v for k, v in report.items() if k != "hash"})
    view = build_export_view(case, report, snapshot)
    rendered = html.unescape(render_html(view))
    pdf = pdfium.PdfDocument(render_pdf(view))
    try:
        extracted = ""
        for i in range(len(pdf)):
            page = pdf[i]
            text = page.get_textpage()
            try:
                extracted += text.get_text_range() + "\n"
            finally:
                text.close()
                page.close()
    finally:
        pdf.close()
    for fact in ("Deterministic transaction reasons", "Recorded analysis coverage and gaps",
                 "rule detect_cycles", "window_hours", "Origin: uploaded", "locator: row/2",
                 "sources/csv-original", report["hash"], snapshot.snapshot_id, source_id):
        assert fact in rendered
        assert fact in extracted
    assert '"generation": 7' in rendered and '"generation": 7' in extracted
    assert "display cap 200" in rendered and "display cap 200" in extracted


def test_pdf_uses_verified_packaged_font_and_rejects_missing_glyphs_explicitly():
    case = generate_case("circular")
    report = make_report(case, transaction_analysis(case))
    report["synthesis"]["summary"] = "François reviews supplied evidence."
    report["hash"] = digest({k: v for k, v in report.items() if k != "hash"})
    assert render_pdf(build_export_view(case, report)).startswith(b"%PDF-")
    report["synthesis"]["summary"] = "Evidence 漢"
    report["hash"] = digest({k: v for k, v in report.items() if k != "hash"})
    view = build_export_view(case, report)
    assert "漢" in render_html(view)
    with pytest.raises(ValueError, match="U\\+6F22.*use HTML"):
        render_pdf(view)
