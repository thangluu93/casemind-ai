import inspect
import hashlib
from decimal import Decimal

import pytest

from casemind.analytics import summarize_activity, transaction_analysis
from casemind.case_resolver import CaseResolver, create_manifest, demo_snapshot, snapshot_from_manifest
from casemind.cloud import Cloud
from casemind.document_rendering import render_document
from casemind.explanations import build_transaction_reasons
from casemind.generator import document_pdf, generate_case
from casemind.models import ActorRef, Evidence, digest
from casemind.source_catalog import SourceCatalog
from casemind.store import Conflict, FileStore


def test_raw_v1_hash_does_not_expand_missing_defaults():
    raw = generate_case("layering").model_dump(mode="json")
    raw.pop("description")
    snapshot_id = digest(raw)
    assert snapshot_id == "cea594e3ff1567dd40dece720b29124ba47022c93293ee95508a80d50d07a191"
    snapshot = snapshot_from_manifest({"hash": snapshot_id, "case": raw})
    assert snapshot.snapshot_id == snapshot_id
    assert digest(snapshot.case) != snapshot_id
    with pytest.raises(ValueError):
        snapshot_from_manifest({"hash": "0" * 64, "case": raw})


def test_v2_hash_and_owner_resolution(tmp_path):
    case = generate_case("layering")
    store = FileStore(tmp_path)
    actor = ActorRef(kind="session", owner_id="owner-a")
    raw = create_manifest(case, {}, {}, owner_id=actor.owner_id)
    snapshot = snapshot_from_manifest(raw)
    store.put(f"inputs/{case.id}/{snapshot.snapshot_id}", raw)
    store.put("owner-cases/" + digest(actor.owner_id), {"cases": {case.id: snapshot.snapshot_id}})
    resolver = CaseResolver(store, {})
    assert resolver.resolve(case.id, actor) == snapshot
    for other in [None, ActorRef(kind="session", owner_id="owner-b")]:
        with pytest.raises(KeyError):
            resolver.resolve(case.id, other)
    assert CaseResolver(store, {case.id: case}).resolve(case.id).case == case
    raw["case"]["title"] = "tampered"
    with pytest.raises(ValueError):
        snapshot_from_manifest(raw)


def test_exact_blobs_staging_generation_and_scans(tmp_path):
    store = FileStore(tmp_path)
    catalog = SourceCatalog(store)
    original = b"\x00exact\r\nbytes\xff"
    ref = catalog.put(original, "application/octet-stream")
    assert catalog.put(original, "application/octet-stream") == ref
    assert catalog.read(ref) == original
    with pytest.raises(Conflict):
        store.put_blob_if_absent(ref.storage_key, b"different", ref.media_type)
    gen = catalog.stage("staging/intake-a", original, ref.media_type)
    with pytest.raises(Conflict):
        store.delete_staging_blob("staging/intake-a", gen + 1)
    assert catalog.promote("staging/intake-a", gen, ref.media_type) == ref
    with pytest.raises(KeyError):
        store.get_blob("staging/intake-a")
    for key in ["history/a", "history/b", "history/c"]:
        store.put(key, {})
    assert store.scan_keys("history/", limit=2) == (["history/a", "history/b"], "history/b")
    assert store.scan_keys("history/", cursor="history/b", limit=2) == (["history/c"], None)
    with pytest.raises(ValueError):
        store.get("/absolute")
    with pytest.raises(ValueError):
        store.scan_keys("history/", limit=1001)


def test_pdf_original_and_inert_derivative(tmp_path):
    catalog = SourceCatalog(FileStore(tmp_path))
    original = document_pdf(generate_case("layering").documents[0])
    ref = catalog.put(original, "application/pdf")
    pages = render_document(original, ref)
    assert len(pages) == 1
    assert pages[0]["bytes"].startswith(b"\x89PNG\r\n\x1a\n")
    assert pages[0]["sha256"] == hashlib.sha256(pages[0]["bytes"]).hexdigest()
    assert pages[0]["original_generation"] == ref.generation
    assert catalog.read(ref) == original
    for malformed in [b"%PDF-1.7 invalid", b"not pdf"]:
        bad_ref = catalog.put(malformed, "application/pdf")
        with pytest.raises(ValueError):
            render_document(malformed, bad_ref)


def expanded_case(count):
    case = generate_case("layering")
    template = case.transactions[0]
    # Equal timestamps deliberately exercise deterministic tie ordering.
    txs = [template.model_copy(update={"id": f"tx-{i:05d}"}) for i in range(count)]
    return case.model_copy(update={"transactions": list(reversed(txs))})


@pytest.mark.parametrize("count", [500, 501, 5000])
def test_cloud_full_pinned_transaction_set(count):
    case = expanded_case(count)
    snapshot = demo_snapshot(case)
    rows = [t.model_dump() for t in sorted(case.transactions, key=lambda t: (t.timestamp, t.id))]
    for row in rows:
        row.pop("source_kind")
    class Query:
        total_bytes_processed = 0
        def result(self, **kwargs):
            return rows
    class Client:
        def query(self, sql, **kwargs):
            assert "LIMIT 5000" in sql
            assert snapshot.snapshot_id[:20] in sql
            return Query()
    cloud = Cloud.__new__(Cloud)
    cloud.bigquery = Client()
    queried = cloud.query_transactions(snapshot)
    assert len(queried.transactions) == count
    assert queried.transactions[0].id == "tx-00000"
    rows[-1] = rows[0]
    with pytest.raises(ValueError, match="integrity"):
        cloud.query_transactions(snapshot)


def test_total_5001_rejected():
    case = expanded_case(5001)
    with pytest.raises(ValueError, match="5000"):
        create_manifest(case, {}, {})
    with pytest.raises(ValueError, match="5000"):
        Cloud.__new__(Cloud).query_transactions(demo_snapshot(case))


def test_roles_order_and_legacy_unknown():
    case = expanded_case(8)
    case.transactions[0].amount = Decimal("100000")
    snapshot = demo_snapshot(case)
    findings = summarize_activity(case)
    assert findings
    ev = findings[0]
    target = ev.target_transaction_id
    assert build_transaction_reasons(snapshot, [ev], target)["status"] == "indicator"
    baseline = next(k for k, v in ev.participant_roles.items() if v == "baseline_context")
    assert build_transaction_reasons(snapshot, [ev], baseline)["status"] == "no_indicator"
    raw = ev.model_dump()
    for field in ["ordered_transaction_ids", "participant_roles", "target_transaction_id", "coverage"]:
        raw.pop(field)
    assert build_transaction_reasons(snapshot, [Evidence(**raw)], target)["status"] == "not_evaluated"
    layering = generate_case("layering")
    for finding in transaction_analysis(layering):
        if finding.tool in ("trace_flows", "detect_cycles") and finding.claim_kind == "indicator":
            txs = {t.id: t for t in layering.transactions}
            ordered = [txs[i] for i in finding.ordered_transaction_ids]
            assert all(a.timestamp < b.timestamp for a, b in zip(ordered, ordered[1:]))


def test_active_pdf_and_resource_caps(tmp_path):
    import io
    from reportlab.pdfgen import canvas
    catalog = SourceCatalog(FileStore(tmp_path))
    # Inline active catalog content is never preserved in the raster output.
    pdf = document_pdf(generate_case("layering").documents[0])
    active = pdf.replace(b"/Type /Catalog", b'/OpenAction << /S /JavaScript /JS (app.alert("blocked")) >> /Type /Catalog')
    ref = catalog.put(active, "application/pdf")
    pages = render_document(active, ref)
    assert b"JavaScript" not in pages[0]["bytes"]
    for page_size, count in [((100000, 100000), 1), ((612, 792), 51)]:
        data = io.BytesIO()
        writer = canvas.Canvas(data, pagesize=page_size)
        for _ in range(count):
            writer.drawString(10, 10, "SYNTHETIC")
            writer.showPage()
        writer.save()
        original = data.getvalue()
        with pytest.raises(ValueError):
            render_document(original, catalog.put(original, "application/pdf"))


def test_page_reservation_is_atomic_and_retains_failed_attempts(tmp_path):
    from casemind.store import UsageLedger
    ledger = UsageLedger(FileStore(tmp_path), max_pages=3)
    ledger.reserve_pages(2, "attempt-one", "a" * 64)
    ledger.reserve_pages(2, "attempt-one", "a" * 64)
    with pytest.raises(ValueError):
        ledger.reserve_pages(2, "attempt-two", "a" * 64)
    assert len(ledger.store.get("usage/prototype-v1")[0]["pages"]) == 2
    ledger.reserve_pages(1, "attempt-two", "b" * 64)


def test_fifty_page_attempt_reservation_replays_without_additional_spend(tmp_path):
    from casemind.store import UsageLedger
    ledger = UsageLedger(FileStore(tmp_path), max_pages=50)
    ledger.reserve_pages(50, "full-original", "a" * 64)
    ledger.reserve_pages(50, "full-original", "a" * 64)
    assert len(ledger.store.get("usage/prototype-v1")[0]["pages"]) == 50
    with pytest.raises(ValueError):
        ledger.reserve_pages(1, "new-attempt", "a" * 64)


def test_expired_execution_blocks_cloud_before_provider():
    class Expired:
        def check(self):
            raise Conflict("expired")
    cloud = Cloud.__new__(Cloud)
    with pytest.raises(Conflict):
        cloud.query_transactions(demo_snapshot(generate_case("layering")), execution=Expired())


def test_publication_reconciles_job_and_fences_terminal_manifest(tmp_path):
    from types import SimpleNamespace
    case = generate_case("layering")
    snapshot = demo_snapshot(case)
    store = FileStore(tmp_path)
    raw = {"hash": snapshot.snapshot_id, "case": case.model_dump(mode="json")}
    key = f"inputs/{case.id}/{snapshot.snapshot_id}"
    store.put(key, raw)
    rows = [t.model_dump() for t in sorted(case.transactions, key=lambda t: (t.timestamp, t.id))]
    for row in rows:
        row.pop("source_kind")
    class Lease:
        expired = False
        def check(self):
            if self.expired:
                raise Conflict("expired")
            return 30
    lease = Lease()
    class Job:
        def result(self, **kwargs):
            lease.expired = True
    class Query:
        total_bytes_processed = 0
        def result(self, **kwargs):
            return rows
    class Client:
        submissions = 0
        def load_table_from_json(self, data, table, job_config, job_id, **kwargs):
            # Reject arguments the pinned BigQuery client would not accept.
            from google.cloud.bigquery import Client as RealClient
            inspect.signature(RealClient.load_table_from_json).bind(
                None, data, table, job_config=job_config, job_id=job_id, **kwargs)
            self.submissions += 1
            self.table, self.schema, self.job_id = table, job_config.schema, job_id
            assert job_id == "snapshot_" + snapshot.snapshot_id
            return Job()
        def get_job(self, job_id, **kwargs):
            assert job_id == self.job_id
            return SimpleNamespace(result=lambda **kwargs: None, destination=self.table)
        def get_table(self, table, **kwargs):
            return SimpleNamespace(num_rows=len(rows), schema=self.schema)
        def query(self, **kwargs):
            return Query()
    # Accept positional SQL like the actual BigQuery client.
    Client.query = lambda self, sql, **kwargs: Query()
    cloud = Cloud.__new__(Cloud)
    cloud.store, cloud.bigquery = store, Client()
    documents = {d.id: document_pdf(d) for d in case.documents}
    with pytest.raises(Conflict):
        cloud.load_case(snapshot, documents, execution=lease)
    assert store.get(key)[0] == raw
    lease.expired = False
    cloud.load_case(snapshot, documents, execution=lease)
    assert store.get(key)[0]["table"] == cloud.bigquery.table
    assert cloud.bigquery.submissions == 1


def test_document_page_mismatch_retains_actual_reservation(tmp_path):
    from types import SimpleNamespace
    from casemind.store import UsageLedger
    case = generate_case("layering")
    cloud = Cloud.__new__(Cloud)
    cloud.store = FileStore(tmp_path)
    cloud.ledger = UsageLedger(cloud.store)
    cloud.processor = "synthetic-test-processor"
    cloud.documents = SimpleNamespace(process_document=lambda **kwargs:
        SimpleNamespace(document=SimpleNamespace(pages=[], text="")))
    doc = case.documents[0]
    with pytest.raises(ValueError, match="page count"):
        cloud.extract(demo_snapshot(case), doc, document_pdf(doc))
    assert len(cloud.store.get("usage/prototype-v1")[0]["pages"]) == 1


def test_png_derivative_preserves_rgb_channel_order(tmp_path):
    import io
    import struct
    import zlib
    from reportlab.pdfgen import canvas
    stream = io.BytesIO()
    writer = canvas.Canvas(stream, pagesize=(10, 10))
    writer.setFillColorRGB(1, 0, 0)
    writer.rect(0, 0, 10, 10, fill=1, stroke=0)
    writer.showPage()
    writer.save()
    pdf = stream.getvalue()
    ref = SourceCatalog(FileStore(tmp_path)).put(pdf, "application/pdf")
    png = render_document(pdf, ref)[0]["bytes"]
    offset, compressed = 8, b""
    while offset < len(png):
        size = struct.unpack("!I", png[offset:offset + 4])[0]
        if png[offset + 4:offset + 8] == b"IDAT":
            compressed += png[offset + 8:offset + 8 + size]
        offset += size + 12
    assert zlib.decompress(compressed)[1:4] == b"\xff\x00\x00"


def make_selected_page_cloud(tmp_path, *, failure=None, max_pages=50):
    """Synthetic SDK responses exercise actual ProcessRequest/Document contracts."""
    import io
    from types import SimpleNamespace
    from google.cloud import documentai
    from reportlab.pdfgen import canvas
    from casemind.store import UsageLedger
    stream = io.BytesIO()
    writer = canvas.Canvas(stream, pagesize=(40, 40))
    for page in range(1, 51):
        writer.drawString(1, 10, f"SYNTHETIC {page}")
        writer.showPage()
    writer.save()
    pdf = stream.getvalue()
    cloud = Cloud.__new__(Cloud)
    cloud.store = FileStore(tmp_path)
    cloud.ledger = UsageLedger(cloud.store, max_pages=max_pages)
    cloud.processor = "synthetic-test-processor"
    calls = []
    def process_document(request, retry, timeout):
        assert isinstance(request, documentai.ProcessRequest)
        assert request.raw_document.content == pdf
        assert retry is None and 0 < timeout <= 30
        selected = list(request.process_options.individual_page_selector.pages)
        assert 1 <= len(selected) <= 15
        calls.append(selected)
        if len(calls) == 2 and failure == "provider":
            raise RuntimeError("Synthetic provider failure")
        text, pages = "", []
        for number in selected:
            label, value = "Registration ID", f"SYN-{number:02d}"
            offset = len(text)
            text += label + "\n" + value + "\n"
            def anchor(start, end):
                return documentai.Document.TextAnchor(text_segments=[
                    documentai.Document.TextAnchor.TextSegment(start_index=start, end_index=end)])
            layout = documentai.Document.Page.Layout
            field = documentai.Document.Page.FormField(
                field_name=layout(text_anchor=anchor(offset, offset + len(label)), confidence=.9),
                field_value=layout(text_anchor=anchor(offset + len(label) + 1,
                                                      offset + len(label) + 1 + len(value)), confidence=.9))
            pages.append(documentai.Document.Page(page_number=number,
                layout=layout(text_anchor=anchor(offset, len(text))), form_fields=[field],
                tokens=[documentai.Document.Page.Token(layout=field.field_value)]))
        if len(calls) == 2 and failure == "count":
            pages.pop()
        if len(calls) == 2 and failure == "identity":
            pages[0].page_number = 1
        entity = documentai.Document.Entity(type_="registration_id", mention_text="SYNTHETIC",
            page_anchor=documentai.Document.PageAnchor(page_refs=[
                documentai.Document.PageAnchor.PageRef(page=0)]))
        return SimpleNamespace(document=documentai.Document(text=text, pages=pages, entities=[entity]))
    cloud.documents = SimpleNamespace(process_document=process_document)
    return cloud, pdf, calls


def test_fifty_original_pages_are_selected_15_15_15_5_with_global_lineage(tmp_path):
    cloud, pdf, calls = make_selected_page_cloud(tmp_path)
    case = generate_case("layering")
    result = cloud.extract(demo_snapshot(case), case.documents[0], pdf)
    assert list(map(len, calls)) == [15, 15, 15, 5]
    assert [page for call in calls for page in call] == list(range(1, 51))
    assert result["page_count"] == 50
    assert len(cloud.store.get("usage/prototype-v1")[0]["pages"]) == 50
    for field in result["fields"]:
        assert field["value"] == f"SYN-{field['page']:02d}"
        anchor = field["anchors"]["value"][0]
        assert result["text"][anchor["start"]:anchor["end"]] == field["value"]
    for batch in result["ocr_batches"]:
        artifact = batch["document"]
        assert [p["page_number"] for p in artifact["pages"]] == batch["selected_pages"]
        assert int(artifact["entities"][0]["page_anchor"]["page_refs"][0]["page"]) == batch["selected_pages"][0] - 1
        segment = artifact["pages"][0]["layout"]["text_anchor"]["text_segments"][0]
        assert int(segment["start_index"]) == batch["text_offset"]
        assert result["text"][int(segment["start_index"]):int(segment["end_index"])].startswith("Registration ID\n")
    assert cloud.extract(demo_snapshot(case), case.documents[0], pdf) == result
    assert len(calls) == 4
    ref = SourceCatalog(cloud.store).put(pdf, "application/pdf")
    assert SourceCatalog(cloud.store).read(ref) == pdf


@pytest.mark.parametrize("failure", ["provider", "count", "identity"])
def test_selected_page_attempt_failure_retains_quota_without_partial_cache(tmp_path, failure):
    cloud, pdf, calls = make_selected_page_cloud(tmp_path, failure=failure)
    case = generate_case("layering")
    with pytest.raises((ValueError, RuntimeError)):
        cloud.extract(demo_snapshot(case), case.documents[0], pdf)
    assert len(calls) == 2
    assert len(cloud.store.get("usage/prototype-v1")[0]["pages"]) == 30
    assert cloud.store.scan_keys("extraction/") == ([], None)


def test_selected_pages_check_quota_before_each_provider_call(tmp_path):
    cloud, pdf, calls = make_selected_page_cloud(tmp_path, max_pages=20)
    case = generate_case("layering")
    with pytest.raises(ValueError, match="allowance"):
        cloud.extract(demo_snapshot(case), case.documents[0], pdf)
    assert len(calls) == 1
    assert len(cloud.store.get("usage/prototype-v1")[0]["pages"]) == 15
    assert cloud.store.scan_keys("extraction/") == ([], None)


def test_selected_page_expired_fence_stops_remaining_calls_and_cache(tmp_path):
    cloud, pdf, calls = make_selected_page_cloud(tmp_path)
    class Lease:
        def check(self):
            if calls:
                raise Conflict("expired")
            return 5
    case = generate_case("layering")
    with pytest.raises(Conflict):
        cloud.extract(demo_snapshot(case), case.documents[0], pdf, execution=Lease())
    assert len(calls) == 1
    assert len(cloud.store.get("usage/prototype-v1")[0]["pages"]) == 15
    assert cloud.store.scan_keys("extraction/") == ([], None)
