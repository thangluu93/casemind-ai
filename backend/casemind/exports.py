"""Script-free offline exports from an immutable common report projection."""
import json
from html import escape
from io import BytesIO

from pydantic import BaseModel, ConfigDict
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .models import Case, SnapshotRef, digest
from .explanations import build_transaction_reasons
from .workspace import evidence_for, scope_for, snapshot_metadata


class ExportSection(BaseModel):
    model_config = ConfigDict(frozen=True)
    title: str
    lines: tuple[str, ...]


class ExportView(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: int = 1
    case_id: str
    run_id: str
    report_hash: str
    report_version: int
    input_hash: str
    snapshot_id: str
    classification: str
    sections: tuple[ExportSection, ...]


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2)


def build_export_view(case: Case, report: dict, snapshot=None, review=None) -> ExportView:
    scope = scope_for(case, report, snapshot)
    evidence = evidence_for(case, report, snapshot)
    report_body = {k: v for k, v in report.items() if k != "hash"}
    if digest(report_body) != report.get("hash"):
        raise ValueError("Report integrity check failed")
    if review and (review.get("report_hash") != report["hash"] or
                   review.get("run_id", report["run_id"]) != report["run_id"]):
        raise ValueError("Review does not belong to pinned report")
    synthesis = report.get("synthesis", {})
    narrative = [synthesis.get("summary", "No synthesis supplied.")]
    for claim in synthesis.get("hypotheses", []):
        narrative.append("Hypothesis: " + claim["text"])
        narrative.append("Evidence: " + ", ".join(claim["evidence_ids"]))
    narrative.extend("Alternative: " + text for text in synthesis.get("alternatives", []))
    narrative.extend("Unresolved: " + text for text in synthesis.get("unresolved", []))
    sections = [ExportSection(title="Investigator summary and hypotheses", lines=tuple(narrative)),
                ExportSection(title="Allowlisted report facts", lines=tuple(_json(report | {
                    "evidence": [item | {"payload": {k: v for k, v in item.get("payload", {}).items() if k != "text"}} for item in report.get("evidence", [])]
                }).splitlines()))]
    metadata = snapshot_metadata(snapshot)
    reason_snapshot = snapshot if isinstance(snapshot, SnapshotRef) else SnapshotRef(case=case, snapshot_id=scope.snapshot_id)
    linked_transactions = sorted({ref for e in evidence for ref in e.refs} & {tx.id for tx in case.transactions})
    reason_lines = [f"Visible {min(200, len(linked_transactions))} of {len(linked_transactions)} evidence-linked transactions; "
                    f"hidden {max(0, len(linked_transactions)-200)}; display cap 200."]
    for transaction_id in linked_transactions[:200]:
        reasons = build_transaction_reasons(reason_snapshot, evidence, transaction_id)
        tx = reasons["observed_transaction"]
        reason_lines.extend((f"Transaction {transaction_id}: {tx['currency']} {tx['amount']}; {tx['sender']} -> {tx['receiver']}; {tx['timestamp']}",
                             f"Evaluation: {reasons['status']}; disposition: {reasons['disposition']}",
                             "Gaps: " + _json(reasons["gaps"])))
        for reason in reasons["reasons"]:
            reason_lines.extend((f"Evidence {reason['evidence_id']}; rule {reason['rule']}; version {reason['version']}; role {reason['role']}",
                                 "Parameters: " + _json(reason["parameters"]),
                                 "Observed facts: " + _json(reason["observed_facts"]),
                                 "Ordered sources: " + _json(reason["ordered_transaction_ids"]),
                                 "Alternatives: " + _json(reason["alternatives"]),
                                 "Gaps: " + _json(reason["gaps"])))
    sections.append(ExportSection(title="Deterministic transaction reasons", lines=tuple(reason_lines)))
    coverage_lines = [f"Pinned report {report['hash']}; version {report['version']}; snapshot {scope.snapshot_id}",
                      "Report gaps: " + _json(report.get("gaps", []))]
    for item in evidence:
        coverage_lines.extend((f"Evidence {item.id}; rule {item.tool}; version {item.tool_version}",
                               "Coverage: " + _json(item.coverage),
                               "Limitations: " + _json(item.limitations)))
    sections.append(ExportSection(title="Recorded analysis coverage and gaps", lines=tuple(coverage_lines)))
    source_ids = sorted({ref for e in evidence for ref in e.refs})
    source_lines = []
    for source_id in source_ids:
        record = case.sources[source_id]
        source_lines.extend((f"Source {source_id}; snapshot {scope.snapshot_id}; hash {digest(record)}",
                             *_json(record.model_dump(mode="json")).splitlines()))
        provenance = metadata.get("source_metadata", {}).get(source_id, {})
        source_lines.append(f"Origin: {provenance.get('origin', 'generated')}; classification: {provenance.get('classification', 'synthetic')}; locator: {provenance.get('locator') or 'not recorded'}")
        original = metadata.get("source_objects", {}).get(source_id) or provenance.get("source_object")
        source_lines.append("Pinned object provenance: " + (_json(original) if original else "not recorded"))
        for item in evidence:
            for lineage in item.document_lineage or []:
                if lineage.get("document_id") == source_id:
                    source_lines.append(f"Document lineage from evidence {item.id}; version {item.tool_version}: " + _json(lineage))
                    pages = lineage.get("derivative_pages")
                    source_lines.append("Inert derivative page references: " + (_json(pages) if pages else "not recorded in pinned evidence; not embedded offline"))
    sections.append(ExportSection(title="Pinned source excerpts", lines=tuple(source_lines)))
    sections.append(ExportSection(title="Offline inspection limitations", lines=(
        "Synthetic case data. Indicators do not establish criminality.",
        "Complete OCR text is excluded from this export. Structured excerpts are pinned to the input hash. Original PDF bytes and inert page images "
        "are not embedded; page locators require the separately preserved original.",
        "Model hypotheses remain hypotheses. A human owns disposition.",
    )))
    if review:
        sections.append(ExportSection(title="Pinned human review",
                                      lines=(f"Review artifact hash {digest(review)}",
                                             *_json(review).splitlines())))
    return ExportView(case_id=case.id, run_id=report["run_id"], report_hash=report["hash"],
                      report_version=report["version"], input_hash=report["input_hash"],
                      snapshot_id=scope.snapshot_id, classification="synthetic",
                      sections=tuple(sections))


def _identity(view: ExportView) -> tuple[str, ...]:
    return (f"Export view version: {view.version}", f"Case: {view.case_id}",
            f"Run: {view.run_id}", f"Snapshot: {view.snapshot_id}",
            f"Input hash: {view.input_hash}", f"Report hash: {view.report_hash}",
            f"Report version: {view.report_version}", f"Classification: {view.classification}")


VI_TITLES = {
    "Investigator summary and hypotheses": "Tóm tắt điều tra và giả thuyết",
    "Allowlisted report facts": "Dữ kiện báo cáo được phép xuất",
    "Deterministic transaction reasons": "Lý do giao dịch tính toán tất định",
    "Recorded analysis coverage and gaps": "Phạm vi phân tích đã ghi nhận và khoảng trống",
    "Pinned source excerpts": "Trích đoạn nguồn đã ghim",
    "Offline inspection limitations": "Giới hạn khi kiểm tra ngoại tuyến",
    "Pinned human review": "Đánh giá của con người đã ghim",
}
VI_IDENTITY = {"Export view version": "Phiên bản bản xuất", "Case": "Hồ sơ", "Run": "Lượt chạy",
               "Snapshot": "Ảnh chụp dữ liệu", "Input hash": "Mã băm đầu vào",
               "Report hash": "Mã băm báo cáo", "Report version": "Phiên bản báo cáo",
               "Classification": "Phân loại"}
VI_NOTICE = ("Bản song ngữ: tiêu đề và nhãn được dịch sẵn. Nội dung tường thuật của mô hình, "
             "dữ kiện và trích đoạn nguồn giữ nguyên bản gốc tiếng Anh, không dịch máy, để "
             "không làm thay đổi bằng chứng. Dữ liệu tổng hợp; các chỉ báo không chứng minh "
             "hành vi phạm tội.")


def render_html(view: ExportView, lang: str = "en") -> str:
    if lang not in ("en", "vi"):
        raise ValueError("Supported export languages are en and vi")
    bilingual = lang == "vi"

    def title(text):
        return f"{VI_TITLES[text]} / {text}" if bilingual and text in VI_TITLES else text

    def identity_line(line):
        label, _, value = line.partition(": ")
        return f"{VI_IDENTITY.get(label, label)} / {line}" if bilingual else line

    identity = "\n".join(escape(identity_line(line)) for line in _identity(view))
    sections = "".join(f"<section><h2>{escape(title(s.title))}</h2><pre>" +
                       "\n".join(escape(line) for line in s.lines) + "</pre></section>"
                       for s in view.sections)
    heading = ("Báo cáo điều tra CaseMind — dữ liệu tổng hợp / CaseMind investigation report"
               if bilingual else "CaseMind investigation report — synthetic data")
    notice = f'<p class="notice">{escape(VI_NOTICE)}</p>' if bilingual else ""
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" '
            'content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;">'
            '<title>CaseMind investigation report</title><style>'
            'body{font-family:system-ui,sans-serif;max-width:70rem;margin:2rem auto;padding:1rem}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere}section{break-inside:auto}'
            '.notice{border-left:3px solid #3ecf8e;padding-left:.75rem}'
            '@media print{body{margin:0;padding:0}}</style></head><body>'
            f'<h1>{escape(heading)}</h1>{notice}'
            f'<pre>{identity}</pre>{sections}</body></html>')


def render_pdf(view: ExportView) -> bytes:
    if "CaseMindVera" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("CaseMindVera", "Vera.ttf"))
    font = pdfmetrics.getFont("CaseMindVera")
    all_text = "\n".join((*_identity(view), *(s.title for s in view.sections),
                           *(line for s in view.sections for line in s.lines)))
    missing = sorted({ord(character) for character in all_text
                      if not character.isspace() and ord(character) not in font.face.charToGlyph})
    if missing:
        raise ValueError("PDF font cannot represent supplied text glyphs " +
                         ", ".join(f"U+{code:04X}" for code in missing[:12]) +
                         "; use HTML or the existing JSON export to preserve these values")
    output = BytesIO()
    styles = getSampleStyleSheet()
    for name in ("BodyText", "Title", "Heading2"):
        styles[name].fontName = "CaseMindVera"
    body = styles["BodyText"]
    body.fontSize = 8
    body.leading = 11
    # Paragraph markup only comes from these literals; untrusted data is text escaped.
    story = [Paragraph("CaseMind investigation report - synthetic data", styles["Title"])]
    for line in _identity(view):
        story.append(Paragraph(escape(line), body))
    for section in view.sections:
        story.extend((Spacer(1, 12), Paragraph(escape(section.title), styles["Heading2"])))
        for line in section.lines:
            text = "".join(c for c in line if c >= " " or c == "\t")
            # Bound text chunks so a large supplied field never creates an unbreakable flowable.
            for offset in range(0, max(1, len(text)), 1000):
                story.append(Paragraph(escape(text[offset:offset+1000]) or "&#160;", body))
    SimpleDocTemplate(output, title="CaseMind investigation report", pageCompression=0).build(story)
    return output.getvalue()
